import pygame
import math
import copy as c
import sounddevice as sd
import numpy as np
import threading

###############################################################################
# Echo Game
###############################################################################

volume = []
sd.default.samplerate = 96000

def print_sound(indata, outdata, frames, time, status):
    volumeNorm = np.linalg.norm(indata) * 10
    curVol = int(volumeNorm)
    if curVol > 100:
        volume.append(curVol)

def captureSound():
    with sd.Stream(callback=print_sound):
        on = True
        while on == True:
            sd.sleep(1)

pygame.mixer.pre_init(44100, 0, 3, 4096)
pygame.mixer.init()

def getFacingHelper(facing):
    if facing[0] > 0 and facing[1] > 0:
        return "SE"
    elif facing[0] > 0 and facing[1] == 0:
        return "E"
    elif facing[0] > 0 and facing[1] < 0:
        return "NE"
    elif facing[0] == 0 and facing[1] < 0:
        return "N"
    elif facing[0] < 0 and facing[1] < 0:
        return "NW"
    elif facing[0] < 0 and facing[1] == 0:
        return "W"
    elif facing[0] < 0 and facing[1] > 0:
        return "SW"            
    elif facing[0] == 0 and facing[1] > 0:
        return "S"  

def getFootstepPos(shoe, facing):
    offset = 25
    cardinal = {"N" : ((0,0),(offset,0)), "W" : ((0,offset),(0,0)), \
                "S" : ((offset,0),(0,0)), "E" : ((0,0),(0,offset))}
    for key in cardinal:
        if facing == key:
            if shoe == "Left":
                return cardinal[key][0]
            return cardinal[key][1]
    ordinal = {"NW" : (-offset-1, -offset-1), "SW" : (-offset-1, offset+1), \
               "SE" : (offset+1, offset+1), "NE" : (offset+1, -offset-1)}
    for key in ordinal:
        if facing == key:
            return ordinal[key]

def getImages(partition):
    allImages = {}
    facing = ["N", "NW", "W", "SW", "S", "SE", "E", "NE"]
    if partition == "Full":
        for k in range(len(facing)):
            im = pygame.transform.rotate(pygame.transform.scale( \
                 pygame.image.load('footsteps.png').convert_alpha(), \
                 (50, 50)), (45*k))
            allImages[facing[k]] = im
        return allImages
    elif partition == "Half":
        for k in range(len(facing)):
            im = pygame.transform.scale(\
                 pygame.image.load('footsteps.png').convert_alpha(), (50, 50))
            cols = 2
            width, height = im.get_size()
            cellWidth, cellHeight = width // cols, height
            images = []
            for i in range(cols):
                subImage = im.subsurface((i * cellWidth, 0, \
                                          cellWidth, cellHeight))
                subImage = pygame.transform.rotate(subImage, (45*k))
                images.append(subImage)
            allImages[facing[k]] = images
        return allImages

def noteSound(sprite, sounds, note):
    if type(sprite) == Gate:
        position = [sprite.x, sprite.y+sprite.height//2]
    else:
        position = [sprite.pos[0]+sprite.width//2, \
                    sprite.pos[1]+sprite.height//2]
    for angle in range(0, 360, 15):
        colors = {"C" : "Red", "D" : "Orange", "E" : "Yellow", \
                  "F" :"Green", "G" : "Dark Green", "A" : "Blue", \
                  "B" : "Indigo", "C2" : "Violet"}
        color = colors[note]
        radian = math.radians(angle)
        path = [math.cos(radian), math.sin(radian)]
        pos = [position[0]+path[0]*10, position[1]+path[1]*10]
        sounds.append(Particle(path, pos, 20, color))

###############################################################################
# Game sprite classes
###############################################################################

class Particle(pygame.sprite.Sprite):
    def __init__(self, speed, pos, lumen, color):
        self.speed = speed
        self.pos = pos
        self.lumen = self.maxLumen = lumen
        self.rad = 5
        self.rate = 8
        self.color = color
        self.rect = pygame.Rect(pos[0]-5, pos[1]-5, 10, 10)

    def reflect(self, norm):
        dotProd1 = (norm[0]*self.speed[0]) + (norm[1]*self.speed[1]) 
        dotProd2 = (norm[0]**2) + (norm[1]**2)
        proj = [None, None]
        for direct in range(len(norm)):
            proj[direct] = (dotProd1/dotProd2) * norm[direct]
            self.speed[direct] -= 2 * proj[direct]

    def update(self, sounds, walls, endGame, showNotes, playTimes):
        self.move()
        if self.lumen == 0:
            sounds.remove(self)
        for wall in walls:
            if pygame.sprite.collide_rect(wall, self):
                if self.color == "White" and type(wall) == Gate \
                and self.lumen >= 60:
                    if pygame.mixer.Sound.get_num_channels(wall.soundFile) \
                    < playTimes:    
                        pygame.mixer.Sound.play(wall.soundFile)
                        endGame.append(True)
                        showNotes.append(True)
                if wall.normal[1] > 0:
                    self.pos[1] = wall.y + wall.height + self.rate
                    self.speed[1] *= -1
                elif wall.normal[1] < 0:
                    self.pos[1] = wall.y - wall.height - self.rate
                    self.speed[1] *= -1
                elif wall.normal[0] > 0:
                    self.pos[0] = wall.x + wall.width + self.rate
                    self.speed[0] *= -1
                elif wall.normal[0] < 0:
                    self.pos[0] = wall.x - wall.width - self.rate
                    self.speed[0] *= -1

    def move(self):
        for direct in range(len(self.pos)):
            self.pos[direct] += self.speed[direct] * self.rate
        self.lumen -= 1
        self.rect = pygame.Rect(self.pos[0]-5, self.pos[1]-5, 10, 10)

    def draw(self, screen, scroll):
        if self.color == "White":
            change = 255 / self.maxLumen
            RGB = 255 - (self.maxLumen-self.lumen) * change
            if RGB < 0:
                RGB = 0
            color = (RGB, RGB, RGB)
        else:
            colors = ["Red", "Orange", "Yellow", "Green", "Dark Green", \
                      "Blue", "Indigo", "Violet"]
            rgbVal = [(255,0,0), (255,127,0), (255,255,0), (0, 255, 0), \
                      (0,100,0), (0,0,255), (75,0,130), (148,0,211)]
            for ind in range(len(colors)):
                if self.color == colors[ind]:
                    color = rgbVal[ind]
        drawPos = (int(self.pos[0]-scroll[0]), int(self.pos[1]-scroll[1]))
        pygame.draw.circle(screen, color, drawPos, self.rad)

class Footstep(pygame.sprite.Sprite):
    def __init__(self, pos, lumen, shoe, facing):
        self.pos = pos
        self.lumen = lumen
        self.shoe = shoe
        self.images = getImages("Half")
        self.facing = facing
        
    def update(self, footsteps):
        self.lumen -= 1
        if self.lumen == 0:
            footsteps.remove(self)
            
    def draw(self, screen, scroll):
        compass = getFacingHelper(self.facing)
        image = self.images[compass]
        offset = getFootstepPos(self.shoe, compass)
        drawPos = (self.pos[0]-scroll[0]+offset[0], \
                   self.pos[1]-scroll[1]+offset[1])
        if self.shoe == "Left":
            screen.blit(image[0], drawPos)
        elif self.shoe == "Right":
            screen.blit(image[1], drawPos)    
       
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, normal, color):
        # Init.
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.normal = normal
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        
    def draw(self, screen, scroll):
        drawX, drawY = int(self.x-scroll[0]), int(self.y-scroll[1])
        drawY = int(self.y-scroll[1])
        pygame.draw.rect(screen, self.color, \
                         [drawX, drawY, self.width, self.height], 0)
        
class Gate(Wall):
    def __init__(self, x, y, width, height, normal, color, soundFile):
        super().__init__(x, y, width, height, normal, color)
        self.soundFile = pygame.mixer.Sound(soundFile)
        
class Player(pygame.sprite.Sprite):
    def __init__(self, width, height):
        t = threading.Thread(target=captureSound)
        t.start()
        self.step = 8
        self.facing = (1, 0) # East
        self.images = getImages("Full")
        self.width, self.height = self.images["N"].get_size()
        self.pos = [width//2-self.width//2, height//2-self.height//2]
        self.hasFlute = True
        self.timer, self.rhythm = -1, 0
        self.moving = self.stepRepeat = False
        self.footSound = pygame.mixer.Sound("Sounds/stepSound.ogg")
        self.rect = pygame.Rect(self.pos[0], self.pos[1], \
                                self.width, self.height)
        self.sequence = []

    def update(self, scroll, keysDown, sounds, footsteps, walls):
        if len(volume) != 0:
            self.realSound(sounds, volume[-1])
            volume.pop()
        self.rhythm += 1
        if self.rhythm >= 40:
            self.sequence.clear()
        movement = [0, 0]
        if 273 in keysDown and keysDown[273]:
            movement[1] -= 1
        if 274 in keysDown and keysDown[274]:
            movement[1] += 1
        if 275 in keysDown and keysDown[275]:
            movement[0] += 1
        if 276 in keysDown and keysDown[276]:
            movement[0] -= 1
        moves = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
        if tuple(movement) != (0, 0):
            self.moving = True
            self.timer += 1
            if self.timer % 20 == 0:
                footsteps.append(Footstep(c.copy(self.pos), 40, "Right", \
                                          self.facing))
                self.stepSound(sounds)
            elif self.timer % 10 == 0:
                footsteps.append(Footstep(c.copy(self.pos), 40, "Left", \
                                          self.facing))
                self.stepSound(sounds)
            for move in moves:
                if tuple(movement) == move:
                    self.move(move, sounds, walls, scroll)
        else:
            self.moving = False
            self.timer = -1

    def move(self, direction, sounds, walls, scroll):
        if direction[0] != 0 and direction[1] != 0:
            newDirect = [None, None]
            for direct in range(len(direction)):
                newDirect[direct] = (1/2)**(1/2) * direction[direct]
            direction = newDirect
        self.facing = direction
        collision = None
        for wall in walls:
            if pygame.sprite.collide_rect(wall, self):
                collision = wall.normal
        for direct in range(len(self.pos)):
            change = self.step * direction[direct]
            if collision == None:
                scroll[direct] += self.step * direction[direct]
                self.pos[direct] += self.step * direction[direct]
            elif collision[direct] > 0:
                if change < 0:
                    continue
                else:
                    scroll[direct] += self.step * direction[direct]
                    self.pos[direct] += self.step * direction[direct]
            elif collision[direct] < 0:
                if change > 0:
                    continue
                else:
                    scroll[direct] += self.step * direction[direct]
                    self.pos[direct] += self.step * direction[direct]
            elif collision[direct] == 0:
                scroll[direct] += self.step * direction[direct]
                self.pos[direct] += self.step * direction[direct]
        self.rect = pygame.Rect(self.pos[0], self.pos[1], \
                                self.width, self.height)
        
    def stepSound(self, sounds):
        for angle in range(0, 360, 10):
            radian = math.radians(angle)
            path = [math.cos(radian), math.sin(radian)]
            pos = [self.pos[0]+self.width//2+path[0]*10, \
                   self.pos[1]+self.height//2+path[1]*10]
            sounds.append(Particle(path, pos, 80, "White"))        

    def realSound(self, sounds, vol):
        for angle in range(0, 360, 15):
            radian = math.radians(angle)
            path = [math.cos(radian), math.sin(radian)]
            pos = [self.pos[0]+self.width//2+path[0]*10, \
                   self.pos[1]+self.height//2+path[1]*10]
            if vol > 255:
                vol = 255
            sounds.append(Particle(path, pos, vol, "White"))  

            
    def draw(self, screen, width, height):
        if self.stepRepeat == False:
            pygame.mixer.Sound.play(self.footSound, loops = 0)
            self.stepRepeat = True
        if self.moving is False:
            pygame.mixer.Sound.stop(self.footSound)
            self.stepRepeat = False
            compass = getFacingHelper(self.facing)
            image = self.images[compass]
            screen.blit(image, (width-25, height-25))

# Using Lukas Peraza pygame framework: 
# http://blog.lukasperaza.com/getting-started-with-pygame/
class PygameGame(object):
    def __init__(self, width=600, height=400, fps=30, title="Echo Game"):
        self.width = width
        self.height = height
        self.fps = fps
        self.title = title
        pygame.init()

    def init(self):
        self.player = Player(self.width, self.height)   
        self.sounds, self.footsteps = [], []
        self.scroll = [0, 0]
        self.endGame, self.notes = [], []
        self.playSequence = self.gameWin = False
        self.wallColor = (255, 255, 255)
        self.tempo = 0
        self.playTimes = 1
        p1 = self.player.pos[0] - 275
        p2 = self.player.pos[1] - 175
        self.level1 = [Wall(150+p1, 50+p2, 800, 6, (0, 1), self.wallColor), 
                       Wall(150+p1, 50+p2, 6, 300, (1, 0), self.wallColor),
                       Wall(150+p1, 350+p2, 600, 6, (0, -1), self.wallColor),
                       Wall(745+p1, 350+p2, 6, 600, (1, 0), self.wallColor),
                       Wall(945+p1, 50+p2, 6, 1500, (-1, 0), self.wallColor),
                       Wall(350+p1, 950+p2, 400, 6, (0, 1), self.wallColor),
                       Wall(350+p1, 950+p2, 6, 200, (1, 0), self.wallColor),
                       Wall(350+p1, 1150+p2, 400, 6, (0, -1), self.wallColor),
                       Wall(750+p1, 1150+p2, 6, 550, (1, 0), self.wallColor),
                       Wall(750+p1, 1700+p2, 700, 6, (0, -1), self.wallColor),
                       Wall(945+p1, 1550+p2, 500, 6, (0, 1), self.wallColor),
                       Wall(1445+p1, 800+p2, 6, 750, (1, 0), self.wallColor),
                       Wall(1445+p1, 1700+p2, 6, 700, (1, 0), self.wallColor),
                       Wall(1615+p1, 950+p2, 6, 700, (-1, 0), self.wallColor),
                       Wall(1615+p1, 1650+p2, 6, 600, (-1, 0), self.wallColor),
                       Wall(1445+p1, 800+p2, 1125, 6, (0, 1), self.wallColor),
                       Wall(1445+p1, 2400+p2, 1125, 6, (0, -1), \
                            self.wallColor),
                       Wall(1615+p1, 950+p2, 800, 6, (0, -1), self.wallColor),
                       Wall(1615+p1, 2250+p2, 800, 6, (0, 1), self.wallColor),
                       Wall(2415+p1, 950+p2, 6, 1300, (1, 0), self.wallColor),
                       Wall(2570+p1, 800+p2, 6, 725, (-1, 0), self.wallColor),
                       Wall(2570+p1, 1675+p2, 6, 725, (-1, 0), self.wallColor),
                       Wall(2570+p1, 1525+p2, 500, 6, (0, 1), self.wallColor),
                       Wall(2570+p1, 1675+p2, 900, 6, (0, -1), self.wallColor),
                       Wall(3070+p1, 1025+p2, 6, 500, (1, 0), self.wallColor),
                       Wall(3300+p1, 1025+p2, 6, 500, (-1, 0), self.wallColor),
                       Wall(3070+p1, 1025+p2, 230, 6, (0, 1), self.wallColor),
                       Wall(3300+p1, 1525+p2, 350, 6, (0, 1), self.wallColor),
                       Wall(3470+p1, 1675+p2, 6, 1000, (1, 0), self.wallColor),
                       Wall(3650+p1, 1525+p2, 6, 350, (-1, 0), self.wallColor),
                       Wall(3650+p1, 1875+p2, 300, 6, (0, 1), self.wallColor),
                       Wall(3650+p1, 2100+p2, 300, 6, (0, -1), self.wallColor),
                       Wall(3950+p1, 1875+p2, 6, 225, (-1, 0), self.wallColor),
                       Wall(3650+p1, 2100+p2, 6, 400, (-1, 0), self.wallColor),
                       Wall(3470+p1, 2675+p2, 630, 6, (0, -1), self.wallColor),
                       Wall(3650+p1, 2500+p2, 450, 6, (0, 1), self.wallColor),
                       Gate(4100+p1, 2500+p2, 6, 175, (-1, 0), \
                            self.wallColor, "Sounds/Licc.ogg")]

    def isKeyPressed(self, key):
        ''' return whether a specific key is being held '''
        return self._keys.get(key, False)
    
    def timerFired(self, time, screen):
        self.player.update(self.scroll, self._keys, self.sounds, \
                           self.footsteps, self.level1)
        for footstep in self.footsteps:
            footstep.update(self.footsteps)
        for sound in self.sounds:
            sound.update(self.sounds, self.level1, self.endGame, \
                         self.notes, self.playTimes)
        if len(self.notes) != 0:
            if self.tempo == 0:
                noteSound(self.level1[-1], self.sounds, "D")
            elif self.tempo == 8:
                noteSound(self.level1[-1], self.sounds, "E")
            elif self.tempo == 16:
                noteSound(self.level1[-1], self.sounds, "F")
            elif self.tempo == 24:
                noteSound(self.level1[-1], self.sounds, "G")
            elif self.tempo == 32:
                noteSound(self.level1[-1], self.sounds, "E")
            elif self.tempo == 48:
                noteSound(self.level1[-1], self.sounds, "C")
            elif self.tempo == 56:
                noteSound(self.level1[-1], self.sounds, "D")
            elif self.tempo > 56:
                self.notes.clear()
                self.tempo = -1
            self.tempo += 1
        
    def mousePressed(self, *pos):
        pass

    def mouseReleased(self, *pos):
        pass

    def mouseMotion(self, *pos):
        pass
    
    def mouseDrag(self, *pos):
        pass
    
    def keyPressed(self, key, mod):
        noteKeys = [49, 50, 51, 52, 53, 54, 55, 56]
        notes = ["C", "D", "E", "F", "G", "A", "B", "C2"]
        if self.player.hasFlute is True and key in noteKeys:
            for i in range(len(noteKeys)):
                if key == noteKeys[i]:
                    note = notes[i]
                    noteSound(self.player, self.sounds, note)
                    noteFile = pygame.mixer.Sound("Sounds/%s.ogg" % note)
                    pygame.mixer.Sound.play(noteFile)
                    self.player.sequence.append(note)
                    self.player.rhythm = 0
                    Licc = ["D", "E", "F", "G", "E", "C", "D"]
                    if len(self.endGame) != 0 and self.player.sequence == Licc:
                        winSong = pygame.mixer.Sound("Sounds/JOHNCENA.ogg")
                        pygame.mixer.Sound.play(winSong, loops = -1)
                        self.gameWin = True
                        print("Game complete!")
        elif key == 32 and len(self.endGame) != 0:
            self.playTimes += 1
                        
    def keyReleased(self, key, mod):
        pass
    
    def redrawAll(self, screen):
        screen.fill((0, 0, 0))
        self.player.draw(screen, self.width//2, self.height//2)
        for footstep in self.footsteps:
            footstep.draw(screen, self.scroll)
        for particle in self.sounds:
            particle.draw(screen, self.scroll)
        # for wall in self.level1:
        #     wall.draw(screen, self.scroll)
        if self.gameWin is True:
            largeText = pygame.font.Font('freesansbold.ttf',115)
            textSurf = largeText.render("You Won!", True, (255,255,255))
            textRect = textSurf.get_rect()
            textRect.center = ((self.width/2),(self.height/2))
            screen.blit(textSurf, textRect)

    def run(self):
        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        # set the title of the window
        pygame.display.set_caption(self.title)

        # Stores all the keys currently being held down
        self._keys = dict()

        # Call game-specific initialization
        self.init()
        playing = True
        while playing:
            time = clock.tick(self.fps)
            self.timerFired(time, screen)
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.mousePressed(*(event.pos))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.mouseReleased(*(event.pos))
                elif (event.type == pygame.MOUSEMOTION and
                      event.buttons == (0, 0, 0)):
                    self.mouseMotion(*(event.pos))
                elif (event.type == pygame.MOUSEMOTION and
                      event.buttons[0] == 1):
                    self.mouseDrag(*(event.pos))
                elif event.type == pygame.KEYDOWN:
                    self._keys[event.key] = True
                    self.keyPressed(event.key, event.mod)
                elif event.type == pygame.KEYUP:
                    self._keys[event.key] = False
                    self.keyReleased(event.key, event.mod)
                elif event.type == pygame.QUIT:
                    playing = False
            screen.fill((255, 255, 255))
            self.redrawAll(screen)
            pygame.display.flip()

        pygame.quit()
        print("Thanks for playing!")
        
echoGame = PygameGame(1000, 800)
echoGame.run()