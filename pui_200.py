#!/usr/bin/env python

import time
import array
import csv
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from collections import deque
from fild import Fild
from head import Head
from stbar import Footer
from upravl import Uprav
from tools import Tools
from common import ViewDataUpr, DataRequest, data_to_byte, load_image, cal_rgb
from common import config, write_config, family, font_size     # read_config
from portthread import PortThread, port_exc
from pathlib import Path
from simpleedit import SimpleEditor
from title import TitleTop
from top_widget import CTkTop
from form import ToplevelHelp


show = config.getboolean('Verbose', 'visible')
scheme = config.get('Font', 'scheme')

one_port = 1

Width = config.getint('Size', 'width')
Height = config.getint('Size', 'height')

trace = print if show else lambda *x: None

# ctk.set_appearance_mode("System")    # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme(scheme)  # Themes: "blue" (standard), "green", "dark-blue"


class BtnStart(ctk.CTkFrame):
    """Фреим кнопи старт и переключателя"""

    def __init__(self, master):
        super().__init__(master, corner_radius=0, border_width=0, border_color="grey75")
        self.root = master.root
        ttk.Separator(self).grid(row=0, column=0, padx=5, sticky="we")
        self.btn_start = ctk.CTkButton(
            master=self,
            image=self.root.im_korabl,
            text=self.root.START,
            width=131,
            text_color=("gray10", "gray90"),
            border_width=2,
            corner_radius=10,
            compound="bottom",
            border_color="#D35B58",
            font=self.root.font,
            fg_color=("gray84", "gray25"),
            hover_color="#C77C78",
            command=self.root.btn_start_,
        )
        self.btn_start.grid(row=1, column=0, padx=70, pady=10, sticky="we")


class RF(ctk.CTkFrame):
    """Правый фрейм"""

    def __init__(self, root):
        super().__init__(root, corner_radius=0, border_width=2, border_color="grey75")
        self.root = root
        self.tools = Tools(self)    # настройки + метки
        self.tools.grid(row=0, column=0, pady=(2, 0), padx=2, sticky="we")
        self.tools.grid_columnconfigure(0, weight=1)
        self.tools.grid_columnconfigure(1, weight=1)

        self.u_panel = Uprav(self)  # панель управления
        self.u_panel.grid(row=1, column=0, pady=(0, 0), padx=2, sticky="nsew")

        self.izl = BtnStart(self)
        # self.izl.grid(row=2, column=0, pady=2, padx=2, sticky="s")
        self.izl.grid(row=2, column=0, columnspan=1, pady=(0, 5), padx=2, sticky="nswe")

        self.btn_start = self.izl.btn_start


class App(ctk.CTk):
    """Корневой класс приложения"""

    WIDTH = 1340
    HEIGHT = 900
    theme_mode = None       # 1-'dark', 0-'light'
    START = "СТАРТ"                                                  # Излучение
    STOP = "СТОП"                                                    # Ожидание

    def __init__(self):

        super().__init__()
        self.title("")
        self.after(300, lambda: self.iconbitmap("spotify.ico"))
        self.xk1 = False                                            # XK_01 разрешить БГ (False)
        self.geometry(f'{Width}x{Height}+100+0')
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.minsize(1080, 680)
        self._wm_state = True                                       # во весь экран True
        # self.toplevel_created = False
        # self.titl = None
        self.theme_mode = 0
        self.s = ttk.Style()                                        # for TSizegrip
        self.s.theme_use("clam")                    # !!!!!!!!!!!!!!!!!!
        appearance_mode = config.getint('Font', 'app_mode')
        # value, self.theme_mode = ("Dark", 1) if appearance_mode else ("Light", 0)
        value = "Dark" if appearance_mode else "Light"
        ctk.set_appearance_mode(value)
        TitleTop(self, "ПУИ-200")
        self._change_appearance_mode(value)
        # ctk.set_appearance_mode('Light')

        self.im_korabl = load_image('korab.png', im_2=None, size=(48, 24))
        self.font = ctk.CTkFont(family=f"{family}", size=font_size)

        self.crashes = 0                                # число сбоев для ППУ Неисправен
        self.crashes_gps = 5                            # число сбоев gps
        self.enable = True
        self.id_timeout = None

        self.delay_mg = config.getfloat('System', 'delay_mg')
        self.delay_sg = config.getfloat('System', 'delay_sg')
        self.delay = self.delay_mg

        self._vz = config.getint('System', 'vz')      # скорость звука
        self._zg = config.getfloat('System', 'zagl')
        self.zona = config.getfloat('System', 'vzona')
        vz = self._vz.to_bytes(2, 'big').decode('latin-1')
        DataRequest.sv = vz

        self.start_work = False                         # пауза

        # для запрета постановки всех меток
        self.loop = tk.BooleanVar(value=False)
        
        self.win = None                                 # нет окна заглубления
        self.choose_gals = False                        # признак выбора галса

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.r_frame = RF(self)
        self.r_frame.grid(row=0, column=1, rowspan=2, sticky="ns", padx=2)
        self.r_frame.rowconfigure(0, weight=1)
        self.r_frame.rowconfigure(1, weight=100)
        self.r_frame.columnconfigure(0, weight=0)

        self.u_panel = self.r_frame.u_panel
        self.tools = self.r_frame.tools
        self.btn_start = self.r_frame.btn_start

        self.head = Head(self)
        self.head.grid(row=0, column=0, padx=(2, 0), sticky="we")
        self.head.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.adr = '$'

        w_scr = self.winfo_screenwidth() - 296
        self.data_deq = deque(maxlen=w_scr)

        self.enable = True
        height = App.HEIGHT + 230
        mod_msg = '200кГц'
        self.board = Fild(self, App.WIDTH + 400, height)                    # экран эхограммы
        self.board.grid(row=1, column=0, sticky="nsew", padx=(2, 0), pady=1)
        self.board.grid_rowconfigure((0, 1), weight=1)  # minsize=80
        self.board.grid_columnconfigure(0, weight=1)

        self.st_bar = Footer(self)                                          # строка состояния
        self.st_bar.grid(row=2, column=0, columnspan=2, sticky="we", pady=(0, 6))
        self.st_bar.grid_columnconfigure(0, weight=1)

        self.g_ser = PortThread(self.gps_read_data)
        self.ser = PortThread(self.on_receive_func)
        msg = self._open_ports(self.ser, self.g_ser)
        self.data_upr = ViewDataUpr('L', 5)                                 # данные для панели управления
        self.u_panel.update_upr(self.data_upr)
        self.send_data = DataRequest()                                      # данные для передачи в ХК 200
        self.answer = False                                                 # флаг принятых данных
        self.reqwest = ''                                                   # тип запроса (data, version, noise)
        self.records = False                                                # флаг записи галса в файл

        self._check_project(self.st_bar)
        self.st_bar.set_device(msg)
        self.st_bar.set_info_gals('')

        self.init_fild()
        self.old_secs = 0

        self.gps_manager = GpsManager(self.g_ser, self)
        self.gps_receive = 0                                                # прием данных с НСП
        self.view_mod(mod_msg)
        self.set_flag = False
        self.view_delay(self.delay)
        self.win_help = None
        self._tick()

    def view_mod(self, msg: str) -> None:
        """Отобразить режим работы"""
        self.st_bar.set_mod(msg)

    def view_delay(self, delay: float) -> None:
        """Отобразить интервал запуска"""
        self.st_bar.set_delay(delay)

    def btn_start_(self) -> None:
        """Обработчик кнопки излучение"""
        if self.btn_start.cget('text') == self.START and not self.start_work:
            self.btn_start.configure(text=self.STOP)
            self.start_work = True
            self._clr_board_tag_all(('version', 'noise'))
            if self.tools.flag_rec:
                self.tools.tick_gals()
                self.tools.flag_rec_color = False
                self.tools.blink_rec()
            self.unbind("<Control-z>")
        else:
            self.btn_start.configure(text=self.START)
            self.start_work = False
            self.bind("<Control-z>", self._full_scr)
            try:
                self.after_cancel(self.tools.id_g)
                self.after_cancel(self.tools.id_rec)
            except ValueError:
                pass
            self._clr_board_tag_all(('glub',))
            self._clr()

    def blink(self, arg=None) -> None:
        """Мигнуть рамкой кнопки излучения"""
        self.btn_start.configure(border_color='green')
        self.after(200, lambda: self.btn_start.configure(border_color='#D35B58'))

    def reset_flag(self) -> None:
        """Сбросить флаг для update_upr"""
        self.set_flag = False

    def gps_read_data(self, data: bytes) -> None:
        """Чтение порта GPS"""
        self.gps_manager.gps_read_data(data)

    def set_local_time(self) -> None:
        """Установка машинного времени в head"""
        t = time.strftime('%d.%m.%y %H:%M:%S')
        arg = ('', '', '', '', t, False)
        self.head.set_(*arg)

    @staticmethod
    def _open_ports(ser: PortThread, g_ser: PortThread) -> str:
        """Открытие портов"""
        port_pui = config.get('Port', 'port_pui')
        baudrate_pui = config.getint('Port', 'baudrate_pui')
        port_gps = config.get('Port', 'port_gps')
        baudrate_gps = config.getint('Port', 'baudrate_gps')
        timeout = config.getfloat('Port', 'timeout')
        timeout_gps = config.getfloat('Port', 'timeout_gps')
        error_p, error_g = '', ''
        try:
            ser.open_port(port_pui)
            ser.tty.baudrate = baudrate_pui
            ser.tty.timeout = timeout
            ser.start()
        except port_exc:
            error_p = 'не'
        if g_ser:
            try:
                g_ser.open_port(port_gps)
                g_ser.tty.baudrate = baudrate_gps
                g_ser.tty.timeout = timeout_gps
                g_ser.start()
            except port_exc:
                error_g = 'не'
        else:
            error_g = 'не'
        msg_1 = (f'Порты:  ППУ  <{port_pui}> {error_p} открыт,'
                 f'   НСП  <{port_gps}> {error_g} открыт.')
        return msg_1

    def init_fild(self) -> None:
        """Создание нового полотна и очередей"""
        self.board.create_fild()
        self.update_idletasks()
        self.bind_()

    def bind_(self) -> None:
        """Привязки событий"""
        self.bind("<Up>", self.board.up)
        self.bind("<Down>", self.board.down)
        self.bind("<Home>", self.board.home)
        self.bind("<End>", self.board.en)
        self.bind("<Alt-F4>", self._on_closing)
        self.bind("<Return>", lambda arg=None: None)
        self.bind("<Control-p>", self.board.all_one_echo)
        self.bind("<Control-l>", self.board.show_duration_echo)
        self.bind("<Control-b>", self.board.fon_color_ch)
        self.bind("<Control-m>", self.board.off_scale)
        self.bind("<Control-t>", self.board.time_metka_on)
        self.bind("<Control-w>", self.board.hide_metki)
        self.bind("<Control-h>", self.create_toplevel_help)
        self.bind("<Control-o>", self.change_app_mode)
        self.bind("<Control-v>", self.get_version)
        self.bind("<Control-n>", self.get_noise)
        self.bind("<Control-e>", self.edit_config)
        self.bind("<Control-z>", self._full_scr)
        self.bind("<Escape>", self._clr)

    def _full_scr(self, arg=None):
        """Развернуть на весь экран"""
        self.state('zoomed') if self._wm_state else self.state('normal')
        self.attributes("-fullscreen", self._wm_state)
        self._wm_state = not self._wm_state
        self._change_appearance_mode('Light')
        self._change_appearance_mode('Dark')

    def _clr_board_tag_all(self,  tag: tuple) -> None:
        """Очистить на холстах элементы с тегами"""
        self.board.clr_item(tag)

    def _clr(self, arg=None) -> None:
        """Обработчик клавиши ESC"""
        self._clr_board_tag_all(('version', 'noise', 'not_data'))

    def _tick(self) -> None:
        """Системный тик"""
        secs = time.time()
        if secs - self.old_secs >= self.delay:                  # задержка 1.0
            self.old_secs = secs
            if self.btn_start.cget('text') == self.STOP:
                self._step_on()
            else:
                self.old_secs = 0
                self._clr_board_tag_all(('error', 'glub'))      # убрать Нет связи с ППУ
                self.board.old_glub = 0
                self.crashes = 0
            if self.gps_receive < 0:
                self.set_local_time()                           # показать локальное время
        self.update()
        self.after(20, self._tick)

    def _step_on(self) -> None:
        """Один цикл работы с модулем 50"""
        # self.t = time.time()
        self.gps_receive -= 1
        if self.enable:
            # print('50')                             # !!!
            self.reqwest = 'data'
            self.answer = False                                # сбросить флаг ответа
            self._clr_board_tag_all(('version', 'noise', 'not_data'))
            dat = data_to_byte(self.send_data)
            trace(f'> {dat}')
            self.crashes += 1
            if self.ser.is_open():
                self.ser.clear_port()
                self.ser.send(dat)                         # посылка данных в ХК без потока
                # self.ser.send_thread(dat)
            if self.crashes >= 3:
                self.crashes = 3
                self.board.create_error('error')            # Надпись Нет связи с ППУ на холст
                self.loop.set(False)

    def on_receive_func(self, data: bytes) -> None:
        """Чтение порта XK"""
        self.update()
        match self.reqwest:
            case 'data':
                if len(data) == 134 and data[-2:] == b'\r\n':
                    if data[0] == 36:                               # $
                        self.crashes = 0
                        self.loop.set(True)
                    else:
                        trace('<@>')
                        return
                    trace(f'{data}')
                    self._work(data[1:-2])
                    self.blink()                                     # мигнуть
                else:
                    trace(f'*{len(data)}')
            case 'version':
                if len(data) > 20:
                    trace(f'v = {data}')
                    self._show_version(data[1:])
            case 'noise':
                if len(data) == 403:
                    trace(f'n = {data}')                             # 403
                    self._show_noise(data[1:])
                # else:
                #     print(f'd = {len(data)}')
        self.update()

    def _work(self, data: bytes) -> None:
        """Режим работа"""
        # self.t = time.perf_counter()
        self.answer = True
        self.board = self.board
        # depth = chr(data[0])
        data_point, data_ampl, data_len = self._parce_data(data)
        # d_len = array.array('f')                 # float 4 bytes (было H 2 bytes)
        # for i in data_len:
        #     d_len.append(self.cal_len(i))
        self._update_data_deque(data_point, data_ampl, data_len)
        self.board.show(data_point, data_ampl, data_len)                    # отобразить на холсте
        if self.records:
            f_gals = self.tools.file_gals
            self._write_gals(f_gals, data_point, data_ampl, data_len)   # если надо, то пишем в файл
        # print(time.perf_counter() - self.t)

    def _update_data_deque(self, data_p: array.array, data_a: array.array, data_l: array.array) -> None:
        """Очередь для хранения данных всего экрана"""
        shot = ([n / 10 for n in data_p],
                data_a, data_l, self.board.mark_type)
        self.data_deq.appendleft(shot)

    def _parce_data(self, data: bytes) -> tuple[array.array, ...]:
        """
        Разбор данных, глубин и амплитуд
        (b'depth,ku,m,cnt,not,g0h,g0l,a0h,a0l,d0h,d0l,
         g1h,g1l,a1h,a1l,c1,l1, ... gnh,gnl,anh,anl,cn,ln')
        """
        zg = int(self._zg * 10)                                           # заглубление
        depth = chr(data[0])
        ku = chr(data[1])
        # ku = data[1]
        send_data = self.send_data
        if self.send_data.rej == 'S':
            send_data.depth = depth                                      # в ручке не обновлять
            send_data.ku = ku
        # print(depth, self.old_depth)
        # if depth != self.old_depth and self.send_data.rej == 'S':     # в ручке не обновлять
        if self.send_data.rej == 'S':
            self.delay = self.change_delay(send_data.depth)             # new
            self.view_delay(self.delay)                                      # вывод время цикла
        m_cnt = data[2]
        cnt = data[3]
        distance = int.from_bytes(data[5:7], 'big')
        distance = distance + zg if distance else 0
        ampl = int.from_bytes(data[7:9], 'big')
        len_ = int.from_bytes(data[9:11], 'big')
        # len__ = self.cal_len(len_)
        # ampl__ = self.cal_ampl(ampl)
        self.data_upr = ViewDataUpr(depth, data[1], cnt, m_cnt, ampl, len_, distance)         # ku = data[1]
        self.u_panel.update_upr(self.data_upr)                  # данные для панели управления
        self.board.view_glub(distance)                              # вывод глубины
        data_point = array.array('H')                               # 'H' 2 bytes 'B' 1 bytes
        data_ampl = array.array('H')
        data_len = array.array('H')
        data_point.append(distance)
        data_ampl.append(ampl)
        data_len.append(len_)
        dat = data[11:]
        cnt = 20 if cnt > 20 else cnt
        for i in range(0, cnt * 4, 4):
            distance = int.from_bytes(dat[i:i+2], 'big') + zg
            ampl = int.from_bytes(dat[i+2:i+4], 'big')
            len_ = int.from_bytes(dat[i+4:i+6], 'big')
            data_point.append(distance)
            data_ampl.append(ampl)
            data_len.append(len_)
        return data_point, data_ampl, data_len

    def change_delay(self, depth: str) -> float:
        """Вычисление периода запуска"""
        if depth == 'L':
            delay = self.delay_mg
        else:
            delay = self.delay_sg
        return delay

    def cal_len(self, cod: int) -> float:
        """Вычислить длительность эхо в см."""
        tic = 10
        # return round(cod * self._vz / 20000)   # round(cod * n * self.vz / 10000, 2) -> float
        return round(cod * self._vz * (tic / 1000000), 2)   #

    def _show_version(self, data: bytes) -> None:
        """Показать номер версии на холсте"""
        self.answer = True
        self._clr_board_tag_all(('noise', 'not_data', 'glub'))
        data = data.decode('latin-1')           # str
        # if len(data) == 33:
        self.board.view_version(data)           # !!

    def _show_noise(self, data: bytes) -> None:
        """Вывести шум на холст"""
        # print(data)
        self.answer = True
        # data = data.decode('latin-1')         # str
        self._clr_board_tag_all(('version', 'not_data', 'glub'))
        # if len(data) == 402:
        # print(len(data))
        self.board.view_noise(data)             # !!

    def get_version(self, arg=None) -> None:
        """Callback для номера версии """
        self._get_noise_version('V')
        self.close_help()

    def get_noise(self, arg=None) -> None:
        """Callback для шума"""
        self._get_noise_version('N')
        self.close_help()

    def _get_noise_version(self, type_) -> None:
        """Получить данные для шума или версии"""
        # b'$NRL05\x05\xdc8c\r\n'                    # request noise     50
        # b'$VRL05\x05\xdc94\r\n'                    # request version   50
        if self.win_help:
            self.win_help.destroy()
        data = self.send_data
        ser = self.ser
        if not self.start_work:
            self.reqwest = 'noise' if type_ == 'N' else 'version'
            work_ = 'N' if type_ == 'N' else 'V'
            work = data.work
            data.work = work_
            start = data.start
            data.start = self.adr
            dat = data_to_byte(data)
            data.work = work
            data.start = start
            # ser.send_thread(dat)
            ser.send(dat)
            self.answer = False
            time.sleep(1)
            self.after(500, self._not_data)

    def _not_data(self) -> None:
        """Вывести на холст Нет данных"""
        if not self.answer:
            self._clr_board_tag_all(('version', 'noise'))
            self.board.create_error('not_data')

    def change_data_upr(self, rej: str, depth: str, ku: int) -> None:
        """Были изменения в ручном режиме обнавляем DataRequest"""
        data = self.send_data
        data.depth = depth
        # data.ku = ku
        data.ku = chr(ku.to_bytes(1, 'big')[0])
        data.rej = rej
        if depth == 'L':
            self.delay = self.delay_mg
        else:
            self.delay = self.delay_sg
        self.view_delay(self.delay)

    def _write_gals(self, filename: Path, data_p: array.array, data_a: array.array,
                    data_l: array.array) -> None:
        """Пишем в файл"""
        data = self.prepare_data_gals(data_p, data_a, data_l)
        # print(data)
        with open(filename, 'a', newline='') as f:
            f_csv = csv.writer(f)
            f_csv.writerow(data)

    def prepare_data_gals(self, data_p: array.array, data_a: array.array, data_l: array.array) -> list:
        """Подготовить данные для записи галса
          (формат, глубина, амплитуда, длительность, объект дата время,
           широта, долгота, скорость, курс, скорость звука, осадка, порог,
           диап. глубин, режим, частота, число стопов, число кор. стопов,
           ручн. метка, цвет ручн. метки , авто метка.)
        """
        format_ = config.get('System', 'fmt')
        # vz = config.getint('System', 'vz')
        vz = self._vz
        zg = self._zg
        dt = self.data_upr
        send_data = self.send_data
        freq = '200'
        depth, ku, cnt, m, ampl, lenth, glub = dt.depth, dt.ku, dt.cnt, dt.m, dt.ampl, dt.len, dt.distance
        # ku += 1           #
        rej = send_data.rej
        try:
            # gps_t, gps_s, gps_d, gps_v, gps_k = self.gps_manager.get_data_gps()
            raise TypeError
        except TypeError:
            gps_t, gps_s, gps_d, gps_v, gps_k = '', '', '', '', ''
        if not gps_t:
            gps_t = time.strftime('%d.%m.%y %H:%M:%S')
        mark_ = self.data_deq[0][-1]
        m_man, m_avto, color_mm = '', '', ''
        if mark_[0]:
            if mark_[1] == 'M':
                m_man = mark_[0]
                color_mm = 'red'
            if mark_[1] == 'A':
                m_avto = mark_[0]
        file_list = [format_, glub, ampl, self.cal_len(lenth)*10, gps_t, gps_s, gps_d, gps_v, gps_k,
                     vz, zg, ku, depth, rej, freq, cnt, m,
                     m_man, color_mm, m_avto]
        for gd, ad, ld in zip(data_p[1:], data_a[1:], data_l[1:]):
            ad_ = cal_rgb(ad)
            file_list.extend([gd, ad_, self.cal_len(ld)*10])
        return file_list

    def pref_form(self, d: str, z: float, vz: int, zona: float) -> None:
        """Возврат результата из формы 'DBT'.., z(заглубл.) если есть изменения и
           переписать config.ini"""
        self._zg = z                                 # изменение заглубл.
        self._vz = vz
        self.zona = zona
        s = vz.to_bytes(2, 'big').decode('latin-1')
        self.send_data.sv = s
        self.tools.update_(f'{z}', d, vz)
        self.head.set_utc()
        config.set('System', 'zagl', f'{z}')
        config.set('System', 'fmt', f'{d}')
        write_config()

    def change_app_mode(self, arg=None) -> None:
        self._change_appearance_mode('Light') if self.theme_mode else self. _change_appearance_mode('Dark')
        self.close_help()
        geometry_str = self.geometry()
        tmp = geometry_str.split('x')
        width = tmp[0]
        tmp2 = tmp[-1].split('+')
        height = tmp2[0]
        x = tmp2[1]
        y = str(int(tmp2[2]) + 1)
        self.geometry(f"{width}x{height}+{x}+{y}")      # дергаем окно

    def _change_appearance_mode(self, new_appearance_mode) -> None:
        """Сменить тему"""
        if new_appearance_mode == 'Dark':
            self.s.configure('TSizegrip', background='grey19')
            self.theme_mode = 1
            # self.app_mode.set(0)
        else:
            self.s.configure('TSizegrip', background='grey82')
            self.theme_mode = 0
            # self.app_mode.set(1)
        ctk.set_appearance_mode(new_appearance_mode)
        config.set('Font', 'app_mode', f'{self.theme_mode}')
        write_config()

    @staticmethod
    def _check_project(st_bar: Footer) -> None:
        """Проверка существования поекта"""
        if not Path(config.get('Dir', 'dirprj')).exists():
            config.set('Dir', 'dirprj', '')
            write_config()
            st_bar.set_info_project('')

    def edit_config(self, arg=None):
        """Редактировать файл config.ini"""
        # window_ = ctk.CTkToplevel(self)
        window_ = CTkTop(title="Config.ini", icon="config", font=self.font,
                         border_width=2, width=1100, height=800)    # btn_close=False,
        frame = ctk.CTkFrame(window_.w_get)
        frame.grid(sticky="nsew")

        SimpleEditor(window_, frame)
        # window_.bind("<Escape>", lambda x: window_.destroy())
        # self.after(300, lambda: self.close_help())
        self.close_help()
        # self.after(300, lambda: self.top.close_help())

    def create_toplevel_help(self, arg=None) -> None:
        """Окно подсказок для привязок"""
        self.top = ToplevelHelp(self)

    def close_help(self, arg=None) -> None:
        """Убрать окно"""
        self.after(300, lambda: self.top.close_help())
        # self.top.close_help()

    def _on_closing(self, arg=None) -> None:
        """Выход"""
        if self.btn_start.cget('text') == self.STOP:
            self.btn_start_()        # Перейти в ожидание если излучение
        self.ser.stop()
        self.g_ser.stop()
        # sys.stdout.flush()
        raise SystemExit()


class GpsManager:
    """Класс работы с НСП(GPS)"""

    def __init__(self, g_ser: PortThread, root):
        self.g_ser = g_ser
        self.root = root
        self.head = self.root.head
        self.crashes_gps = 5
        self.data_gps = None
        self.zona = config.getfloat('System', 'vzona')

    def gps_read_data(self, data: bytes) -> None:
        """Приём из НСП в потоке
        '$GPRMC,123519.xxx,A,4807.038x,N,01131.000x,E,x22.4,084.4,230394,003.1,W*6A\n'
        123419 – UTC время 12:34:19, А – статус, 4807.038,N – Широта, 01131.000,Е – Долгота,
        022.4 – Скорость, 084.4 – Направление движения, 230394 – Дата, 003.1,W – Магнитные вариации
        """
        # print(f'<< {data}')
        self.root.gps_receive = 2
        if data:
            self.crashes_gps = 0
            data = data.decode('latin-1').split(',')[1:10]      # list[str...]
            if len(data) == 9:
                self._parse_data_gps(data)
            else:
                self.crashes_gps += 1
        else:
            self.crashes_gps += 1
        if self.crashes_gps > 3:
            self.crashes_gps = 3
            self.root.set_local_time()

    def _parse_data_gps(self, data: list) -> None:
        """Разбор данных gps"""
        # print('+')
        try:
            s_ = data[2].split('.')
            d_ = data[4].split('.')
            sh = f"{s_[0][:-2]} {s_[0][-2:]}.{s_[1][:3]} {data[3]}"  # {0xB0:c} °
            d = f"{d_[0][:-2]} {d_[0][-2:]}.{d_[1][:3]} {data[5]}"
        except IndexError:
            sh = d = ''
        try:
            str_struct = time.strptime(data[0].split('.')[0] + data[8], "%H%M%S%d%m%y")
            t_sec = time.mktime(str_struct)
            t_sec += self.zona * 3600
            str_struct = time.localtime(t_sec)
            t = time.strftime("%d.%m.%y %H:%M:%S", str_struct)
        except (IndexError, ValueError):
            t = ''
        try:
            vs = f"{float(data[6]):=04.1f}"          # ! 05.1f
            k = f"{float(data[7]):=05.1f}"
        except (IndexError, ValueError):
            vs = k = ''
        self.head.set_(sh, d, vs, k, t, True)       # только если излучение
        self.data_gps = (t, sh, d, vs, k)

    def get_data_gps(self) -> tuple:
        """Вернуть данные GPS"""
        return self.data_gps


if __name__ == "__main__":
    app = App()
    # app.attributes("-fullscreen", True)       # во весь экран без кнопок
    # app.state('zoomed')                       # развернутое окно
    app.mainloop()
