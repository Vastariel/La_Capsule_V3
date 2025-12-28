#!/usr/bin/python
#coding: utf-8

import time

import RPi.GPIO as GPIO

import pygame
from pygame.locals import *
pygame.init()
pygame.font.init()

from pilots import encoder
import menu
import api

#CONSTANTS
HOME_WIFI_IP="192.168.1.159"
RPC_PORT=50008
FPS=30
SCREEN_SIZE=(720, 1280)

#ASSETS
BACKGROUND_PATH="assets/bg16-9.png"
NUM_FONT_PATH="assets/DS-DIGI.TTF"
TXT_FONT_PATH="assets/Rubik-VariableFont_wght.ttf"

#COLORS
WHITE=pygame.Color("White")
BLACK=pygame.Color("Black")
COLOR_BG=pygame.Color(22,13,34,255)
COLOR_HL=pygame.Color(255,255,255,255)

class Num() :
    def __init__(self,api,pos,name,format_value,font_size,numb_of_num,decimals=0) :
        self.pos = pos
        self.name = name
        self.format = format_value
        self.font = pygame.font.Font(NUM_FONT_PATH,font_size)
        self.numb_of_num=numb_of_num
        self.decimals=decimals
    def render(self) :
        value=api.ACCESS_VALUES[self.name]
        formated_value=self.format(value,self.numb_of_num,self.decimals)+"  "
        return self.font.render(formated_value,1,COLOR_HL,COLOR_BG)

def format_distance(value,numb_of_num,decimals=0,type=None) :
    rounded_value=round(value,decimals)
    if decimals==0 :
        txt=str(rounded_value).zfill(numb_of_num)
    else :
        txt=str(rounded_value).zfill(numb_of_num+1+decimals)
    if numb_of_num>=12 :
        txt=f"{txt[:9]}.{txt[9:]}"
    if numb_of_num>=9 :
        txt=f"{txt[:6]}.{txt[6:]}"
    if numb_of_num>=6 :
        txt=f"{txt[:3]}.{txt[3:]}"
    return txt

class Main() :
    def __init__(self,api,debug=False) :

        self.api=api

        #vars
        self.fps=FPS
        self.size=SCREEN_SIZE
        self.debug=debug

        #working
        self.on=False
        self.clock=pygame.time.Clock()
        self.screen=pygame.display.set_mode(self.size,pygame.FULLSCREEN)
        self.bg=pygame.image.load(BACKGROUND_PATH).convert_alpha()
        self.bg=pygame.transform.scale(self.bg,SCREEN_SIZE)
        self.fps_font=font=pygame.font.SysFont("Arial", 30)

        #menu
        self.menu=menu.Menu((50,1030),font_size=27,color_bg=COLOR_BG,color_hl=COLOR_HL,font_path=TXT_FONT_PATH)
        
        self.menu.add_button(menu.Button("PAUSE",self.toggle_pause_game,["un","1"]))
        self.menu.add_button(menu.Button("CONSEILS",print,["deux","2"]))
        self.menu.add_button(menu.Button("EN SAVOIR PLUS",print,["trois","3"]))
        self.menu.add_button(menu.Button("RELANCER LA MISSION",print,["quatre","4"]))
        self.menu.add_button(menu.Button("DEBUG",self.toogle_debug,["cinq","5"]))

        #GPIO
        encoder.GAUCHE=self.menu.gauche
        encoder.DROITE=self.menu.droite
        encoder.BOUTTON=self.menu.click

        #num
        self.nums=[]
        self.nums.append(Num(api,(30,805),"altitude",format_distance,80,9))
        self.nums.append(Num(api,(230,320),"speed",format_distance,70,6,1))

    def launch(self) :
        self.on=True
        self.screen.blit(self.bg,(0,0))
        while self.on :
            #Start of loop
            #self.screen.blit(self.bg,(0,0))

            #Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.on = False
                #if pygame.mouse.get_pressed() :
                #    print("STOP")
                #    self.on = False
            
            #Add Menu
            self.screen=self.menu.show(self.screen)

            #Add Nums
            for num in self.nums :
                self.screen.blit(num.render(),num.pos)

            #Add header
            if self.debug :
                self.show_header()

            #Add debug
            if self.debug :
                self.show_debug()

            #End of loop
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
    
    def show_header(self) :
        fps=str(round(self.clock.get_fps(),1))
        fps_api=self.api.get_fps()
        txt=f"DEBUG MODE | screen_fps : {fps} | apis_fps : {fps_api}"
        to_blit=self.fps_font.render(txt,1,WHITE,BLACK)
        self.screen.blit(to_blit,(10,10))
    
    def show_debug(self) :
        for i,key in enumerate(self.api.access_values) :
            txt=f"{key} : {self.api.access_values[key]}"
            to_blit=self.fps_font.render(txt,1,WHITE,BLACK)
            font_size=self.fps_font.size(txt)[1]
            self.screen.blit(to_blit,(10,font_size*2+((font_size+5)*i)))

    def toogle_debug(self,args) :
        if self.debug :
            self.debug=False
        else :
            self.debug=True
        self.clean_screen()
    
    def toggle_pause_game(self,args) :
        if self.api.con.krpc.paused :
            self.api.con.krpc.paused=False
        else :
            self.api.con.krpc.paused=True
            
    def clean_screen(self) :
        self.screen.blit(self.bg,(0,0))

api = api.API(fps=10)
api.connect()
api.start()


tele=Main(api)


tele.launch()

api.is_running = False
api.join()


