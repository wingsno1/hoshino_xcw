import nonebot
import json

from datetime import timedelta
from hoshino import Service, priv, config
from quart import request,session,redirect,Blueprint
from .data_source import render_template,get_random_str

switcher = Blueprint('switcher',__name__)
bot = nonebot.get_bot()
app = bot.server_app
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = get_random_str(10)

public_address = config.IP #改为你服务器的公网ip,域名应该也可以，我没试过
port = config.PORT
passwd = config.PassWord #登录密码

sv_help = '''
服务开关网页端
私聊[bot设置]
'''.strip()

sv = Service(
    name = '网页服务开关',  #功能名
    use_priv = priv.SUPERUSER, #使用权限   
    manage_priv = priv.SUPERUSER, #管理权限
    visible = False, #False隐藏
    enable_on_default = True, #是否默认启用
    bundle = '通用', #属于哪一类
    help_ = sv_help #帮助文本
    )

@sv.on_fullmatch(["帮助网页服务开关"])
async def bangzhu(bot, ev):
    await bot.send(ev, sv_help, at_sender=True)

@switcher.before_request
async def _():
    user_ip = request.remote_addr
    if request.path == '/svlogin':
        return
    if request.path == '/check':
        return
    if session.get('user_ip') == user_ip:
        return
    return redirect('/svlogin') 

@switcher.route('/svlogin',methods=['GET','POST'])
async def login():
    print(request.method)
    if request.method == 'GET':
        return await render_template('login.html',passwd=passwd,public_address=public_address,port=port)
    else:
        login_data = await request.form
        input_psd = login_data.get('password')
        if input_psd == passwd:
            user_ip = request.remote_addr
            session['user_ip'] = user_ip
            session.permanent = True
            app.permanent_session_lifetime = timedelta(weeks=2)
            return redirect('/svmanager')
        else:
            return redirect('/svlogin')


@switcher.route('/svmanager')
async def svmanager():
    return await render_template('main.html',public_address=public_address,port=port)

@switcher.route('/svgroup')
async def test():
    groups = await get_groups()
    return await render_template('by_group.html',items=groups,public_address=public_address,port=port)

@switcher.route('/svservice')
async def show_all_services():
    svs = Service.get_loaded_services()
    sv_names = list(svs)
    return await render_template('by_service.html',items=sv_names,public_address=public_address,port=port)

@switcher.route('/svgroup/<gid_str>')
async def show_group_services(gid_str:str):
    gid = int(gid_str)
    svs = Service.get_loaded_services()
    conf = {}
    conf[gid_str] = {}
    for key in svs:
        conf[gid_str][key] = svs[key].check_enabled(gid)
    return await render_template('group_services.html',group_id=gid_str,conf=conf,public_address=public_address,port=port)

@switcher.route('/svservice/<sv_name>')
async def show_service_groups(sv_name:str):
    svs = Service.get_loaded_services()
    groups = await get_groups()
    conf = {}
    for group in groups :
        gid = group['group_id']
        gid_str = str(gid)
        conf[gid_str] = {}
        if svs[sv_name].check_enabled(gid):
            conf[gid_str][sv_name] = True
        else:
            conf[gid_str][sv_name] = False
    return await render_template('service_groups.html',sv_name=sv_name,conf=conf,groups=groups,public_address=public_address,port=port)

async def get_groups():
    return await bot.get_group_list()

@switcher.route('/svset/',methods=['GET','POST'])
async def set_group():
    #接收前端传来的配置数据，数据格式{"<gid>":{'serviceA':True,'serviceB':False}}
    if request.method == 'POST':
        data = await request.get_data()
        conf = json.loads(data.decode())
        svs = Service.get_loaded_services()
        for k in conf:
            gid = int(k)
            for sv_name in conf[k]:
                if conf[k][sv_name]:
                    svs[sv_name].set_enable(gid)
                    svs[sv_name].logger.info(f'启用群 {gid} 服务 {sv_name} ')
                else:
                    svs[sv_name].set_disable(gid)
                    svs[sv_name].logger.info(f'禁用群 {gid} 服务 {sv_name}')
        return 'ok'


@bot.on_message('private')
async def setting(ctx):
    message = ctx['raw_message']
    if message in ['服务管理', 'bot设置']:
        await bot.send(ctx,f'http://{public_address}:{port}/svmanager',at_sender=False)
