#!/usr/bin/env python3
from ansible_playbook_runner import Runner
from jinja2 import Environment, FileSystemLoader
from io import StringIO
from flask import Flask, render_template, request, session, send_file
import re
import sys
import webbrowser
import os, os.path
from os import path
import ast
import time

def idealop_playb(ideal_op_id, jun_idprom_cmd):
    #########################################################################################
    with open('tmp_auth_dict.json') as fl:
        auth_dict = ast.literal_eval(fl.read().strip())
    tb_path = auth_dict['TB']['ansi_path']
    sw_func, sw_vendor, username, passwd = auth_dict['TB']['sw_func'], auth_dict['TB']['sw_vendor'], auth_dict['TB']['usrname'], auth_dict['TB']['pass']
    #########################################################################################

    env = Environment(loader=FileSystemLoader('.'))
    templ = env.get_template(tb_path +"/idealop_playb.j2")

    with open(tb_path + "/idealop_playb.yml", "w") as fl:
        fl.write(templ.render(id_int=ideal_op_id, jun_idprom_cmd=jun_idprom_cmd, sw_func=sw_func, sw_vendor=sw_vendor, username=username, passwd=passwd))

    ########Run endpoint_playb.yml, pull TX and RX powers and compare with TX and RX powers in test bed optics#############3
    pbrun = Runner([tb_path + '/inventory/inven.ini'], tb_path + '/idealop_playb.yml')
    res = pbrun.run()

#########Run app########################
if __name__ == '__main__':
    idealop_playb()
