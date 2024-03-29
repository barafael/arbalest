#! /usr/bin/python
#    This file is part of Slingshot.
#
# Slingshot is a two-dimensional strategy game where two players attempt to shoot one
# another through a section of space populated by planets.  The main feature of the
# game is that the shots, once fired, are affected by the gravity of the planets.

# Slingshot is Copyright 2007 Jonathan Musther and Bart Mak. It is released under the
# terms of the GNU General Public License version 2, or later if applicable.

# Slingshot is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation; either
# version 2 of the License, or any later version.

# Slingshot is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Slingshot;
# if not, write to
# the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA


# ABOUT THE CODE:
# This code was intended as prototyping code. It turned out to become the whole game. We use
# this python version as our alpha release. Bugs will be fixed, but in the mean time the game
# will be ported to c++/sdl. Our beta release will be c++/sdl and from that point this python
# version will no longer be supported.
# This code lacks a good structure and comments.

# Copyright (C) 2009 Marcus Dreier <m-rei@gmx.net>
# Copyright (C) 2010 Ryan Kavanagh <ryanakca@kubuntu.org>

import os
import sys
import threading
from random import randint
import pygame

from game.inputbox import *
from game.network import *
from game.menu import *
from game.particle import *
from game.planet import *
from game.player import *
from game.general import *
from game.settings import *
from pygame.locals import *


sys.path.insert(0, "/usr/share/games")


class Game:

    particle_image = None
    particle_image_rect = None
    last = 1

    pygame.font.init()
    Settings.font = pygame.font.Font(get_data_path("FreeSansBold.ttf"), 14)
    Settings.menu_font = pygame.font.Font(
        get_data_path("FreeSansBold.ttf"), Settings.MENU_FONT_SIZE
    )
    Settings.round_font = pygame.font.Font(get_data_path("FreeSansBold.ttf"), 100)
    Settings.fineprint = pygame.font.Font(get_data_path("FreeSansBold.ttf"), 8)

    def __init__(self):
        pygame.display.init()

        self.clock = pygame.time.Clock()

        self.screen = pygame.display.set_mode((800, 600))
        icon, _ = load_image("icon64x64.png", (0, 0, 0))
        pygame.display.set_icon(icon)
        pygame.display.set_caption("Slingshot")

        Settings.particle_image10, Settings.particle_image10_rect = load_image(
            "explosion-10.png", (0, 0, 0)
        )
        Settings.particle_image5, Settings.particle_image5_rect = load_image(
            "explosion-5.png", (0, 0, 0)
        )

        Settings.menu_background, Settings.menu_rect = load_image("menu.png", (0, 0, 0))
        Settings.box, _ = load_image("box.png", (0, 0, 0))
        Settings.tick, _ = load_image("tick.png", (0, 0, 0))
        Settings.tick_inactive, _ = load_image("tick_inactive.png", (0, 0, 0))

        self.trail_screen = pygame.Surface(self.screen.get_size())
        self.trail_screen = self.trail_screen.convert()
        self.trail_screen.set_colorkey((0, 0, 0))
        self.trail_screen.set_alpha(125)

        self.planet_screen = pygame.Surface(self.screen.get_size())
        self.planet_screen = self.trail_screen.convert()
        self.planet_screen.set_colorkey((0, 0, 0))

        self.dim_screen = pygame.Surface(self.screen.get_size())
        self.dim_screen.set_alpha(175)
        self.dim_screen = self.dim_screen.convert_alpha()
        # self.dim_screen.fill((0,0,0))

        self.background, _ = load_image("backdrop.png")

        self.players = (Dummy(), Player(1), Player(2))
        self.playersprites = pygame.sprite.RenderPlain(
            (self.players[1], self.players[2])
        )
        self.missile = Missile(self.trail_screen)
        self.missilesprite = pygame.sprite.RenderPlain((self.missile))

        self.net_client = False
        self.net_host = False

        self.load_settings()

        if self.fullscreen:
            self.use_fullscreen()

        # self.fixed_power = Settings.FIXED_POWER
        # self.bounce = Settings.BOUNCE
        # self.invisible = Settings.INVISIBLE
        # self.random = Settings.RANDOM
        # self.timeout = Settings.MAX_FLIGHT

        # self.max_planets = Settings.MAX_PLANETS
        # self.max_rounds = Settings.MAX_ROUNDS

        self.main_menu = Menu("Menu", copyright=True)
        self.main_menu.add("Back to game")
        self.main_menu.add("New game")
        self.main_menu.add("New network game")
        self.main_menu.add("Settings")
        self.main_menu.add("Help")
        self.main_menu.add("Quit")

        self.confirm_menu1 = Confirm(
            "Starting a new game", "will apply new settings", "and reset the scores"
        )
        self.confirm_menu1.add("Yes")
        self.confirm_menu1.add("No")

        self.confirm_menu2 = Confirm("Starting a new game", "will reset the scores")
        self.confirm_menu2.add("Yes")
        self.confirm_menu2.add("No")

        self.apply_menu = Confirm(
            "This will start a", "new game and reset", "the scores"
        )
        self.apply_menu.add("Yes")
        self.apply_menu.add("No")

        self.settings_menu = Menu("Settings")
        self.settings_menu.add("Back")
        self.settings_menu.add("Game style")
        self.settings_menu.add("Game options")
        self.settings_menu.add("Apply settings")
        self.settings_menu.add("Graphics")

        self.net_menu = Menu("Network game")
        self.net_menu.add("Back")
        self.net_menu.add("Host a game")
        self.net_menu.add("Connect to a host")

        self.net_host_menu = Menu("Waiting for a client")
        self.net_host_menu.add("Back")

        self.net_error_menu = Menu("Network error")
        self.net_error_menu.add("Back")

        self.style_menu = Menu("Game style")
        self.style_menu.add("Back")
        self.style_menu.addoption("Random", self.random)
        self.style_menu.addoption("Fixed power", self.fixed_power, not self.random)
        self.style_menu.addoption("Bounce", self.bounce, not self.random)
        self.style_menu.addoption("Invisible planets", self.invisible, not self.random)

        self.mode_menu = Menu("Game options")
        self.mode_menu.add("Back")
        self.mode_menu.add("Max number of planets")
        self.mode_menu.add("Max number of black holes")
        self.mode_menu.add("Number of rounds")
        self.mode_menu.add("Shot timeout")

        self.timeout_menu = Numeric("Shot timeout", self.timeout, 250, 2000, 500)

        self.graphics_menu = Menu("Graphics")
        self.graphics_menu.add("Particles")
        self.graphics_menu.add("Full Screen")

        self.planet_menu = Numeric(
            "Maximum number of planets", self.max_planets, 1, 8, 2
        )

        self.blackholes_menu = Numeric(
            "Maximum number of black holes", self.max_blackholes, 1, 3, 0
        )

        self.particles_menu = Menu("Particle")
        self.particles_menu.add("Back")
        self.particles_menu.add("On")
        self.particles_menu.add("Off")

        self.fullscreen_menu = Menu("Full Screen")
        self.fullscreen_menu.add("Back")
        self.fullscreen_menu.add("On")
        self.fullscreen_menu.add("Off")

        self.rounds_menu = Numeric(
            "Number of rounds", self.max_rounds, 1, 100, 0, "Infinite"
        )

        self.help_menu = Help()

        self.welcome_menu = Welcome()

        self.menu = self.welcome_menu

        self.q = False

        self.message = ""
        self.score_message = ""

        self.started = False

        self.lock = threading.Lock()

        self.game_init()

    def game_init(self, net_client=False, net_host=False):
        self.new_game(net_client, net_host)
        self.round_init()
        self.bounce_count = 255
        self.bounce_count_inc = 7

    def settings_changed(self):
        result = False

        if Settings.MAX_PLANETS != self.max_planets:
            result = True
        if Settings.MAX_FLIGHT != self.timeout:
            result = True
        if Settings.BOUNCE != self.bounce:
            result = True
        if Settings.INVISIBLE != self.invisible:
            result = True
        if Settings.FIXED_POWER != self.fixed_power:
            result = True
        if Settings.MAX_ROUNDS != self.max_rounds:
            result = True
        if Settings.RANDOM != self.random:
            result = True
            if Settings.FULLSCREEN != self.fullscreen:
                result = True

        return result

    def new_game(self, net_client=False, net_host=False):
        Settings.MAX_PLANETS = self.max_planets
        Settings.BOUNCE = self.bounce
        Settings.INVISIBLE = self.invisible
        Settings.FIXED_POWER = self.fixed_power
        Settings.MAX_ROUNDS = self.max_rounds
        Settings.RANDOM = self.random
        Settings.MAX_FLIGHT = self.timeout
        Settings.MAX_BLACKHOLES = self.max_blackholes

        # is there an old network game but the new is none
        if self.net_play() and not net_client and not net_host:
            self.net.close()

        self.net_client = net_client
        self.net_host = net_host

        if self.net_play():
            self.player = 1  # client always begins
        else:
            self.player = randint(1, 2)

        self.round = 0
        self.players[1].reset_score()
        self.players[2].reset_score()
        self.game_over = False

    def round_init(self):
        pygame.key.set_repeat(Settings.KEY_DELAY, Settings.KEY_REPEAT)

        if self.round == Settings.MAX_ROUNDS:
            self.new_game(self.net_client, self.net_host)

        if Settings.RANDOM and self.net_play():
            Settings.BOUNCE = randint(0, 1) == 1
            Settings.FIXED_POWER = randint(0, 1) == 1
            Settings.INVISIBLE = randint(0, 1) == 1

        self.round_over = False

        if not self.net_client:
            self.players[1].init()
            self.players[2].init()
            planetlist = None
        else:
            packet = self.client_round_init()
            planetlist = packet[0]
            y_coordlist = packet[1]

            self.players[1].init(y_coordlist[0])
            self.players[2].init(y_coordlist[1])

        self.missile.flight = 0

        self.firing = 0
        self.particlesystem = pygame.sprite.RenderPlain()

        self.planetsprites = self.create_planets(planetlist)

        self.trail_screen.fill((0, 0, 0))

        self.round += 1

        if self.players[1].score < self.players[2].score:
            self.player = 1
        elif self.players[2].score < self.players[1].score:
            self.player = 2

        if self.net_play() and not self.active_net_player():
            threading.Thread(self.thread_job, ())

        self.show_round = 100
        if Settings.INVISIBLE:
            self.show_planets = 100
        else:
            self.show_planets = 0

        if self.net_host:
            self.host_round_init()

    def toggle_menu(self):
        if self.menu is None:
            self.menu = self.main_menu
        elif self.menu == self.main_menu:
            self.menu = None
        elif self.menu == self.particles_menu:
            self.menu = self.graphics_menu
        elif self.menu == self.fullscreen_menu:
            self.menu = self.graphics_menu
        elif self.menu == self.rounds_menu:
            self.menu = self.mode_menu
        elif self.menu == self.planet_menu:
            self.menu = self.mode_menu
        elif self.menu == self.blackholes_menu:
            self.menu = self.mode_menu
        elif self.menu == self.mode_menu:
            self.menu = self.settings_menu
        elif self.menu == self.style_menu:
            self.menu = self.settings_menu
        elif self.menu == self.timeout_menu:
            self.menu = self.mode_menu
        elif self.menu == self.rounds_menu:
            self.menu = self.settings_menu
        elif self.menu == self.net_error_menu:
            self.menu = self.net_menu
        elif self.menu == self.net_host_menu:
            self.menu = self.net_menu
        else:
            self.menu = self.main_menu

        # if self.menu == self.main_menu:
        #     self.menu.reset()
        if self.menu is not None:
            self.menu.reset()

        if self.menu is None:
            pygame.key.set_repeat(Settings.KEY_DELAY, Settings.KEY_REPEAT)
            self.started = True
        else:
            pygame.key.set_repeat()

    def create_particlesystem(self, pos, n, size):
        if Settings.PARTICLES:
            if Settings.BOUNCE:
                nn = n / 2
            else:
                nn = n
        # for i in range(nn):
        # self.particlesystem.add(Particle(pos, size))

    def create_planets(self, planetlist=None):
        result = pygame.sprite.RenderPlain()

        if planetlist is None:
            if Settings.MAX_BLACKHOLES > 0:
                n = randint(1, Settings.MAX_BLACKHOLES)
                for _ in range(n):
                    result.add(Blackhole(result, self.background))
            else:
                # Only have planets if we don't have any
                # blackholes.
                n = randint(2, Settings.MAX_PLANETS)
                for _ in range(n):
                    result.add(Planet(result, self.background))
        else:
            for p in planetlist:
                if p[0] > Settings.MAX_PLANETS:
                    # Numbers above Settings.MAX_PLANETS are
                    # allocated to blackholes.
                    result.add(Blackhole(None, self.background, p[0], p[1], p[2], p[3]))
                else:
                    result.add(Planet(None, self.background, p[0], p[1], p[2], p[3]))
        return result

    def change_angle(self, a):
        self.players[self.player].change_angle(a)

    def change_power(self, p):
        self.players[self.player].change_power(p)

    def fire(self):
        if self.round_over:
            self.round_init()
        elif not self.firing:
            self.missile.launch(self.players[self.player])
            self.players[self.player].attempts += 1
            self.last = self.player
            self.player = 0
            self.firing = 1
            pygame.key.set_repeat()

    def draw_zoom(self):
        normal_screen = pygame.Surface((800, 600))
        normal_screen.set_colorkey((0, 0, 0))
        normal_screen.convert_alpha()
        self.playersprites.draw(normal_screen)
        if not Settings.INVISIBLE:
            self.planetsprites.draw(normal_screen)

        zoom_screen = pygame.Surface((600, 450))
        zoom_screen.set_colorkey((0, 0, 0))
        zoom_screen.convert_alpha()

        background = pygame.transform.scale(self.background, (600, 450))
        zoom_screen.blit(self.background, (0, 0))
        normal_screen = pygame.transform.scale(normal_screen, (200, 150))
        zoom_screen.blit(normal_screen, (200, 150))

        missilesprite = self.missile.get_image()
        missilesprite = pygame.transform.scale(
            missilesprite,
            (missilesprite.get_size()[0] / 3, missilesprite.get_size()[1] / 3),
        )
        pos = self.missile.get_pos()
        pos = (
            200 + pos[0] / 4 - missilesprite.get_width() / 2,
            150 + pos[1] / 4 - missilesprite.get_height() / 2,
        )
        zoom_screen.blit(missilesprite, pos)

        pygame.draw.rect(zoom_screen, (255, 255, 255), pygame.Rect(0, 0, 600, 450), 1)
        pygame.draw.rect(
            zoom_screen, (150, 150, 150), pygame.Rect(200, 150, 200, 150), 1
        )
        self.screen.blit(self.dim_screen, (0, 0))
        self.screen.blit(zoom_screen, (100, 75))

    def draw(self):
        self.screen.blit(self.background, (0, 0))

        if Settings.BOUNCE:
            pygame.draw.rect(
                self.screen, (self.bounce_count, 0, 0), pygame.Rect(0, 0, 800, 600), 1
            )

        show_planets = False
        if not Settings.INVISIBLE:
            show_planets = True
        else:
            if self.round_over:
                if self.show_planets > 0:
                    for p in self.planetsprites:
                        p.fade(self.show_planets)
                    self.planetsprites.draw(self.screen)
                    self.show_planets -= 1
                else:
                    show_planets = True
        if show_planets:
            self.planetsprites.draw(self.screen)
        self.screen.blit(self.trail_screen, (0, 0))
        self.playersprites.draw(self.screen)
        # self.players[1].draw(self.screen)
        # self.players[2].draw(self.screen)
        # print(self.particlesystem)
        if Settings.PARTICLES:
            self.particlesystem.draw(self.screen)
        if self.firing:
            if self.missile.visible():
                self.missilesprite.draw(self.screen)
        # print(self.planetsprites)
        if self.firing:
            if not self.missile.visible():
                self.draw_zoom()
        self.players[1].draw_status(self.screen)
        self.players[2].draw_status(self.screen)
        if not self.round_over:
            self.players[self.player].draw_info(self.screen)
            self.players[self.player].draw_line(self.screen)
        else:
            if self.show_round > 30:
                txt = Settings.round_font.render("Game Over", 1, (255, 255, 255))
                tmp = pygame.Surface(txt.get_size())
                tmp = tmp.convert_alpha()
                tmp.blit(txt, (0, 0))
                tmp = tmp.convert()
                tmp.set_alpha(2 * self.show_round - 60)
                tmp.set_colorkey((0, 0, 0))
                tmp = tmp.convert_alpha()
                rect = tmp.get_rect()
                s = (100 - self.show_round) * rect.h / 15
                tmp = pygame.transform.scale(tmp, (int(rect.w / rect.h * s), int(s)))
                rect = tmp.get_rect()
                rect.center = (399, 299)
                self.screen.blit(tmp, rect.topleft)
                self.show_round /= 1.04
            elif self.show_planets <= 0:
                dim = pygame.Surface(self.end_round_msg.get_size())
                dim.set_alpha(175)
                dim = dim.convert_alpha()

                rect = self.end_round_msg.get_rect()
                rect.center = (399, 299)

                self.screen.blit(dim, rect.topleft)
                self.screen.blit(self.end_round_msg, rect.topleft)

        if self.firing:
            self.missile.draw_status(self.screen)
        elif self.started:
            if Settings.MAX_ROUNDS > 0:
                txt = Settings.font.render(
                    f"Round {self.round} of {Settings.MAX_ROUNDS}",
                    1,
                    (255, 255, 255),
                )
            else:
                txt = Settings.font.render(f"Round {self.round}", 1, (255, 255, 255))
            rect = txt.get_rect()
            rect.midbottom = (399, 594)
            self.screen.blit(txt, rect.topleft)

        if self.started and not self.game_over:
            if self.show_round > 30:
                txt = Settings.round_font.render(
                    f"Round {self.round}", 1, (255, 255, 255)
                )
                tmp = pygame.Surface(txt.get_size())
                tmp = tmp.convert_alpha()
                tmp.blit(txt, (0, 0))
                tmp = tmp.convert()
                tmp.set_alpha(2 * self.show_round - 60)
                tmp.set_colorkey((0, 0, 0))
                tmp = tmp.convert_alpha()
                rect = tmp.get_rect()
                s = (100 - self.show_round) * rect.h / 25
                tmp = pygame.transform.scale(tmp, (int(rect.w / rect.h * s), int(s)))
                rect = tmp.get_rect()
                rect.center = (399, 299)
                self.screen.blit(tmp, rect.topleft)
                self.show_round /= 1.04

        if self.menu is not None:
            if self.menu.dim:
                self.screen.blit(self.dim_screen, (0, 0))
            img = self.menu.draw()
            rect = img.get_rect()
            rect.center = (399, 299)
            self.screen.blit(img, rect.topleft)

        pygame.display.flip()

    def update_particles(self):
        if Settings.PARTICLES:
            for p in self.particlesystem:
                # print(p.get_pos())
                if p.update(self.planetsprites) == 0 or p.flight < 0:
                    if p.flight >= 0 and p.in_range():
                        if p.get_size() == 10:
                            self.create_particlesystem(
                                p.get_impact_pos(), Settings.n_PARTICLES_5, 5
                            )
                    # print("removing: ", p.get_pos())
                    self.particlesystem.remove(p)
                if p.flight > Settings.MAX_FLIGHT:
                    self.particlesystem.remove(p)

    def end_shot(self):
        pygame.event.clear()
        self.player = 3 - self.last
        if self.menu == None:
            pygame.key.set_repeat(Settings.KEY_DELAY, Settings.KEY_REPEAT)
        self.firing = 0

    def menu_action(self):
        c = self.menu.get_choice()
        if self.menu == self.planet_menu:
            if c >= 0:
                self.max_planets = c
                self.toggle_menu()
                if self.menu == self.blackholes_menu:
                    if c >= 0:
                        self.max_blackholes = c
                        self.toggle_menu()
        if self.menu == self.rounds_menu:
            if c >= 0:
                self.max_rounds = c
                self.toggle_menu()
        if self.menu == self.timeout_menu:
            if c >= 0:
                self.timeout = c
                self.toggle_menu()
        if self.menu == self.particles_menu:
            if c == "On":
                Settings.PARTICLES = True
                self.toggle_menu()
            if c == "Off":
                Settings.PARTICLES = False
                self.toggle_menu()
        if self.menu == self.fullscreen_menu:
            if c == "On":
                self.fullscreen = True
                self.use_fullscreen()
                self.toggle_menu()
            if c == "Off":
                self.fullscreen = False
                self.use_window()
                self.toggle_menu()
        if c == "Quit":
            self.q = True
        elif c == "Back":
            self.toggle_menu()
        elif c == "Start":
            self.started = True
            self.menu = None
        elif c == "Back to game":
            self.toggle_menu()
        elif c == "Apply settings":
            self.menu = self.apply_menu
        elif c == "New game":
            if self.settings_changed():
                self.menu = self.confirm_menu1
            else:
                self.menu = self.confirm_menu2
        elif c == "Number of rounds":
            self.menu = self.rounds_menu
        elif c == "Shot timeout":
            self.menu = self.timeout_menu
        elif c == "Game style":
            self.menu = self.style_menu
        elif c == "Random":
            self.random = not self.random
            self.style_menu.change_active("Bounce", not self.random)
            self.style_menu.change_active("Invisible planets", not self.random)
            self.style_menu.change_active("Fixed power", not self.random)
        elif c == "Help":
            self.menu = self.help_menu
        elif c == "Yes":
            self.menu = None
            self.save_settings()
            self.game_init()
        elif c == "No":
            self.toggle_menu()
        elif c == "Settings":
            self.menu = self.settings_menu
        elif c == "New network game":
            self.menu = self.net_menu
        elif c == "Host a game":
            self.menu = self.net_host_menu
            threading.Thread(target=self.host_game_init)
        elif c == "Connect to a host":
            in_box = Inputbox(self.screen, "Hostname")
            hostname = in_box.ask()
            if hostname is not False:
                self.client_game_init(hostname)
        elif c == "Game options":
            self.menu = self.mode_menu
        elif c == "Graphics":
            self.menu = self.graphics_menu
        elif c == "Shot timeout":
            self.menu = self.timeout_menu
        elif c == "Fixed power":
            self.fixed_power = not self.fixed_power
        elif c == "Bounce":
            self.bounce = not self.bounce
        elif c == "Invisible planets":
            self.invisible = not self.invisible
        elif c == "Max number of planets":
            self.menu = self.planet_menu
        elif c == "Max number of black holes":
            self.menu = self.blackholes_menu
        elif c == "Particles":
            self.menu = self.particles_menu
        elif c == "Full Screen":
            self.menu = self.fullscreen_menu

    def update(self):
        self.update_particles()
        if self.firing:
            self.firing = self.missile.update(self.planetsprites, self.players)
        if self.missile.flight < 0 and not self.missile.visible():
            self.firing = 0
        if self.firing <= 0:
            # Collision between missile and planet (0) or
            # a black hole (-1).
            #
            # Don't create any particles when we hit a black
            # hole, the missile got sucked up.
            if self.firing == 0 and self.missile.visible():
                self.create_particlesystem(
                    self.missile.get_impact_pos(), Settings.n_PARTICLES_10, 10
                )
                self.end_shot()

        if self.net_play() and not self.active_net_player():
            threading.start_new_thread(self.thread_job, ())

        if self.menu is not None:
            self.menu_action()
        if self.players[1].shot or self.players[2].shot:
            if self.players[1].shot:
                self.players[1].update_explosion()
            else:
                self.players[2].update_explosion()
            pygame.key.set_repeat()
            if not self.round_over:
                self.end_round()
        if self.menu is None:
            self.started = True

        self.bounce_count += self.bounce_count_inc
        if self.bounce_count > 255 or self.bounce_count < 125:
            self.bounce_count_inc *= -1
            self.bounce_count += 2 * self.bounce_count_inc

    def end_round(self):
        self.round_over = True

        if self.round == Settings.MAX_ROUNDS:
            offset1 = 50
        else:
            offset1 = 0

        power_penalty = self.missile.get_score()
        for i in range(1, 3):
            if self.players[i].shot:
                if self.player == 3 - i:
                    message = f"Player {i} killed self"
                    score = Settings.SELFHIT
                    score_message = f"{score} deducted from score"
                    self.players[i].add_score(-score)
                    killed_self = True
                else:
                    message = f"Player {3 - i} killed player {i}"
                    if self.players[3 - i].attempts == 1:
                        bonus = Settings.QUICKSCORE1
                    elif self.players[3 - i].attempts == 2:
                        bonus = Settings.QUICKSCORE2
                    elif self.players[3 - i].attempts == 3:
                        bonus = Settings.QUICKSCORE3
                    else:
                        bonus = 0
                    killed_self = False
                    score = power_penalty + bonus + Settings.HITSCORE
                    score_message = "{score} added to score"
                    self.players[3 - i].add_score(score)

                if not killed_self:
                    offset = 40
                else:
                    offset = 0

                if self.round == Settings.MAX_ROUNDS:
                    offset2 = 40
                else:
                    offset2 = 0

                self.end_round_msg = pygame.Surface(
                    (450, 190 + offset + offset1 + offset2)
                )
                self.end_round_msg.set_colorkey((0, 0, 0))
                self.end_round_msg.fill((0, 0, 0))

                if self.round == Settings.MAX_ROUNDS:
                    msg = Settings.menu_font.render("Game over", 1, (255, 255, 255))
                    rect = msg.get_rect()
                    rect.midtop = (224, 28)
                    self.end_round_msg.blit(msg, rect.topleft)

                msg = Settings.font.render(message, 1, (255, 255, 255))
                rect = msg.get_rect()
                rect.midtop = (224, 28 + offset1)
                self.end_round_msg.blit(msg, rect.topleft)

                if not killed_self:
                    msg = Settings.font.render("Hit opponent:", 1, (255, 255, 255))
                else:
                    msg = Settings.font.render("Hit self:", 1, (255, 255, 255))
                rect = msg.get_rect()
                rect.topleft = (50, 65 + offset1)
                self.end_round_msg.blit(msg, rect.topleft)

                if not killed_self:
                    msg = Settings.font.render(
                        f"{Settings.HITSCORE}", 1, (255, 255, 255)
                    )
                else:
                    msg = Settings.font.render(
                        f"{Settings.SELFHIT}", 1, (255, 255, 255)
                    )
                rect = msg.get_rect()
                rect.topright = (399, 65 + offset1)
                self.end_round_msg.blit(msg, rect.topleft)

                if not killed_self:
                    msg = Settings.font.render("Quickhit bonus:", 1, (255, 255, 255))
                    rect = msg.get_rect()
                    rect.topleft = (50, 85 + offset1)
                    self.end_round_msg.blit(msg, rect.topleft)

                    msg = Settings.font.render(f"{bonus}", 1, (255, 255, 255))
                    rect = msg.get_rect()
                    rect.topright = (399, 85 + offset1)
                    self.end_round_msg.blit(msg, rect.topleft)

                    msg = Settings.font.render("Power penalty:", 1, (255, 255, 255))
                    rect = msg.get_rect()
                    rect.topleft = (50, 105 + offset1)
                    self.end_round_msg.blit(msg, rect.topleft)

                    msg = Settings.font.render(f"{power_penalty}", 1, (255, 255, 255))
                    rect = msg.get_rect()
                    rect.topright = (399, 105 + offset1)
                    self.end_round_msg.blit(msg, rect.topleft)

                msg = Settings.font.render(score_message, 1, (255, 255, 255))
                rect = msg.get_rect()
                rect.midtop = (224, 100 + offset + offset1)
                self.end_round_msg.blit(msg, rect.topleft)

                if self.round == Settings.MAX_ROUNDS:
                    self.show_round = 100
                    self.game_over = True
                    if self.players[1].score > self.players[2].score:
                        winner = 1
                    elif self.players[2].score > self.players[1].score:
                        winner = 2
                    else:
                        winner = 0
                    Settings.font.set_bold(True)
                    if winner != 0:
                        msg = Settings.font.render(
                            f"Player {winner} has won the game", 1, (255, 255, 255)
                        )
                    else:
                        msg = Settings.font.render(
                            "The game has ended in a tie", 1, (255, 255, 255)
                        )
                    Settings.font.set_bold(False)
                    rect = msg.get_rect()
                    rect.midtop = (224, 140 + offset + offset1)
                    self.end_round_msg.blit(msg, rect.topleft)

                if self.round < 10:
                    msg = Settings.font.render(
                        "Press fire for a new round or escape for the menu",
                        1,
                        (255, 255, 255),
                    )
                else:
                    msg = Settings.font.render(
                        "Press fire for a new game or escape for the menu",
                        1,
                        (255, 255, 255),
                    )
                rect = msg.get_rect()
                rect.midtop = (224, 140 + offset + offset1 + offset2)
                self.end_round_msg.blit(msg, rect.topleft)

                pygame.draw.rect(
                    self.end_round_msg,
                    (150, 150, 150),
                    self.end_round_msg.get_rect(),
                    1,
                )

    def run(self):
        while not self.q:
            self.clock.tick(Settings.FPS)
            # print(self.clock.get_fps())

            for event in self.event_check():
                if event.type == QUIT:
                    self.q = True
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.toggle_menu()

                    if self.menu is None and (
                        not self.net_play() or self.active_net_player()
                    ):
                        if (
                            event.mod == KMOD_CTRL
                            or event.mod == KMOD_LCTRL
                            or event.mod == KMOD_RCTRL
                            or event.mod == 4160
                            or event.mod == 4224
                        ):
                            p = 1
                            a = 0.25
                        elif (
                            event.mod == KMOD_SHIFT
                            or event.mod == KMOD_LSHIFT
                            or event.mod == KMOD_RSHIFT
                            or event.mod == 4097
                            or event.mod == 4098
                        ):
                            p = 25
                            a = 5
                        elif (
                            event.mod == KMOD_ALT
                            or event.mod == KMOD_LALT
                            or event.mod == KMOD_RALT
                            or event.mod == 4352
                            or event.mod == 20480
                            or event.mod == 4608
                        ):
                            p = 0.2
                            a = 0.05
                        else:
                            p = 10
                            a = 2

                        if not self.round_over:
                            if event.key == K_UP:
                                self.change_power(p)
                            elif event.key == K_DOWN:
                                self.change_power(-p)
                            elif event.key == K_LEFT:
                                self.change_angle(-a)
                            elif event.key == K_RIGHT:
                                self.change_angle(a)

                        if event.key in [K_RETURN, K_SPACE]:
                            if self.net_play():
                                if (
                                    self.net.send(
                                        (
                                            self.players[self.player].get_angle(),
                                            self.players[self.player].get_power(),
                                            True,
                                        )
                                    )
                                    == False
                                ):
                                    self.menu = self.net_error_menu
                                    self.net.close()
                            self.fire()
                        else:
                            if self.net_play():
                                if (
                                    self.net.send(
                                        (
                                            self.players[self.player].get_angle(),
                                            self.players[self.player].get_power(),
                                            False,
                                        )
                                    )
                                    == False
                                ):
                                    self.menu = self.net_error_menu
                                    self.net.close()

                    elif self.menu is not None:
                        if event.key == K_UP:
                            self.menu.up()
                        elif event.key == K_DOWN:
                            self.menu.down()
                        elif event.key == K_LEFT:
                            self.menu.left()
                        elif event.key == K_RIGHT:
                            self.menu.right()
                        elif event.key == K_RETURN or event.key == K_SPACE:
                            self.menu.select()

            self.lock.acquire()
            self.update()
            self.draw()
            self.lock.release()

        self.save_settings()

    def load_settings(self):

        self.bounce = Settings.BOUNCE
        self.fixed_power = Settings.FIXED_POWER
        self.invisible = Settings.INVISIBLE
        self.random = Settings.RANDOM
        self.max_planets = Settings.MAX_PLANETS
        self.max_blackholes = Settings.MAX_BLACKHOLES
        self.timeout = Settings.MAX_FLIGHT
        self.max_rounds = Settings.MAX_ROUNDS
        self.fullscreen = Settings.FULLSCREEN

        path = os.path.expanduser("~") + "/.slingshot/settings"

        if os.path.exists(path):
            f = open(path, "r")
            lines = f.readlines()
            for l in lines:
                tokens = l.split()
                if tokens[0] == "Bounce:":
                    if tokens[1] == "1":
                        self.bounce = True
                if tokens[0] == "Fixed_Power:":
                    if tokens[1] == "1":
                        self.fixed_power = True
                elif tokens[0] == "Particles:":
                    if tokens[1] == "1":
                        Settings.PARTICLES = True
                elif tokens[0] == "Fullscreen:":
                    if tokens[1] == "1":
                        self.fullscreen = True
                elif tokens[0] == "Random:":
                    if tokens[1] == "1":
                        self.random = True
                elif tokens[0] == "Invisible:":
                    if tokens[1] == "1":
                        self.invisible = True
                elif tokens[0] == "Max_Blackholes:":
                    self.max_blackholes = int(tokens[1])
                elif tokens[0] == "Max_Planets:":
                    self.max_planets = int(tokens[1])
                elif tokens[0] == "Timeout:":
                    self.timeout = int(tokens[1])
                elif tokens[0] == "Rounds:":
                    self.max_rounds = int(tokens[1])
            f.close()

    def save_settings(self):

        path = os.path.expanduser("~") + "/.slingshot"
        if not os.path.exists(path):
            os.mkdir(path)
        path += "/settings"
        f = open(path, "wt")
        if self.bounce:
            f.write("Bounce: 1\n")
        else:
            f.write("Bounce: 0\n")
        if self.fixed_power:
            f.write("Fixed_Power: 1\n")
        else:
            f.write("Fixed_Power: 0\n")
        if self.invisible:
            f.write("Invisible: 1\n")
        else:
            f.write("Invisible: 0\n")
        if self.random:
            f.write("Random: 1\n")
        else:
            f.write("Random: 0\n")
        if Settings.PARTICLES:
            f.write("Particles: 1\n")
        else:
            f.write("Particles: 0\n")
            if self.fullscreen:
                f.write("Fullscreen: 1\n")
            else:
                f.write("Fullscreen: 0\n")
        f.write(f"Max_Planets: {self.max_planets}\n")
        f.write(f"Max_Blackholes: {self.max_blackholes}\n")
        f.write(f"Timeout: {self.timeout}\n")
        f.write(f"Rounds: {self.max_rounds}\n")
        f.close()

    def net_play(self):
        if self.net_host or self.net_client:
            return True
        else:
            return False

    def active_net_player(self):
        if self.player == 1 and self.net_client or self.player == 2 and self.net_host:
            return True
        else:
            return False

    def thread_job(self):
        while 1:
            player_event = self.net.recv()

            self.lock.acquire()
            # Player want no network play anymore
            if not self.net_play():
                break
            if not player_event:
                self.net.close()
                self.menu = self.net_error_menu
                break

            self.change_angle(player_event[0] - self.players[self.player].get_angle())
            self.change_power(player_event[1] - self.players[self.player].get_power())

            if player_event[2]:
                self.fire()

            self.update()
            self.draw()

            if player_event[2]:
                break
            self.lock.release()
        self.lock.release()

    def event_check(self):
        self.lock.acquire()
        result = pygame.event.get()
        self.lock.release()
        return result

    def host_game_init(self):
        if self.net_play():
            self.net.close()

        self.net = Network(3999)
        while 1:
            # Menu changed - player want no network game anymore
            if self.menu != self.net_host_menu:
                return

            ret = self.net.wait_for_cnct()

            # No timeout for accept()
            if ret != -1:
                break

        if not ret:
            packet = (
                self.bounce,
                self.fixed_power,
                self.invisible,
                self.random,
                self.max_planets,
                self.timeout,
                self.max_rounds,
                self.max_blackholes,
            )
            if not self.net.send(packet):
                self.menu = self.net_error_menu
                self.net.close()
                return
            self.menu = None
            self.save_settings()
            self.game_init(net_host=True)
        else:
            self.menu = self.net_error_menu
            self.net.close()

    def client_game_init(self, hostname):
        if self.net_play():
            self.net.close()

        self.net = Network(3999)

        if self.net.cnct(hostname) != False:
            packet = self.net.recv()
            if packet == False:
                self.menu = self.net_error_menu
                self.net.close()
                return

            self.bounce = packet[0]
            self.fixed_power = packet[1]
            self.invisible = packet[2]
            self.random = packet[3]
            self.max_planets = packet[4]
            self.timeout = packet[5]
            self.max_rounds = packet[6]
            self.max_blackholes = packet[7]

            self.menu = None
            self.save_settings()
            self.game_init(net_client=True)
        else:
            self.menu = self.net_error_menu
            self.net.close()

    def host_round_init(self):
        planetlist = []
        for planet in self.planetsprites:
            planetlist.append(
                (
                    planet.get_n(),
                    planet.get_radius(),
                    planet.get_mass(),
                    planet.get_pos(),
                )
            )

        y_coordlist = (
            self.players[1].get_rect_y_coord(),
            self.players[2].get_rect_y_coord(),
        )

        packet = (planetlist, y_coordlist)
        if self.net.send(packet) == False:
            self.menu = self.net_error_menu
            self.net.close()

    def client_round_init(self):
        ret = self.net.recv()
        if ret == False:
            self.menu = self.net_error_menu
            self.net.close()
        return ret

    def use_fullscreen(self):
        pygame.display.set_mode((0, 0), FULLSCREEN | NOFRAME)

    def use_window(self):
        pygame.display.set_mode((800, 600))


def main():
    path = os.path.expanduser("~") + "/.slingshot"
    if not os.path.exists(path):
        os.mkdir(path)
    path += "/logfile.txt"
    sys.stderr = open(path, "w")
    sys.stdout = sys.stderr
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
