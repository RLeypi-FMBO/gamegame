import pygame
import sys
import random
import math
import os
from pygame import mixer

# Инициализация Pygame
pygame.init()
mixer.init()

# Настройки экрана
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Abobik")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
ORANGE = (255, 165, 0)

# Шрифты
font = pygame.font.SysFont('Arial', 24)
title_font = pygame.font.SysFont('Arial', 48)

# Звуки (заглушки, если файлы не найдены)
class DummySound:
    def play(self): pass

try:
    attack_sound = mixer.Sound('attack.wav')
except:
    attack_sound = DummySound()

try:
    parry_sound = mixer.Sound('parry.wav')
except:
    parry_sound = DummySound()

try:
    enemy_hit_sound = mixer.Sound('enemy_hit.wav')
except:
    enemy_hit_sound = DummySound()

try:
    player_hit_sound = mixer.Sound('player_hit.wav')
except:
    player_hit_sound = DummySound()

try:
    boss_shoot_sound = mixer.Sound('boss_shoot.wav')
except:
    boss_shoot_sound = DummySound()

# Класс для загрузки и управления анимациями
class Animation:
    def __init__(self, sprite_name, frames_count, frame_duration=5, loop=True):
        self.frames = []
        self.frame_count = frames_count
        self.current_frame = 0
        self.frame_duration = frame_duration
        self.frame_timer = 0
        self.loop = loop
        self.done = False
        
        # Загрузка кадров анимации
        for i in range(frames_count):
            frame_path = f"sprites/{sprite_name}-{i}.png" if frames_count > 1 else f"sprites/{sprite_name}.png"
            try:
                frame = pygame.image.load(frame_path).convert_alpha()
                self.frames.append(frame)
            except:
                # Если файл не найден, создаем заглушку
                dummy_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.rect(dummy_surface, (255, 0, 0) if "enemy" in sprite_name else (0, 0, 255), 
                               (0, 0, 30, 30))
                self.frames.append(dummy_surface)
        
        # Если кадров нет, создаем один пустой кадр
        if not self.frames:
            dummy_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.rect(dummy_surface, (255, 0, 0) if "enemy" in sprite_name else (0, 0, 255), 
                           (0, 0, 30, 30))
            self.frames.append(dummy_surface)
    
    def update(self):
        if self.frame_count <= 1:
            return
        
        self.frame_timer += 1
        if self.frame_timer >= self.frame_duration:
            self.frame_timer = 0
            self.current_frame += 1
            
            if self.current_frame >= self.frame_count:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.frame_count - 1
                    self.done = True
    
    def get_current_frame(self):
        return self.frames[self.current_frame]
    
    def reset(self):
        self.current_frame = 0
        self.frame_timer = 0
        self.done = False

# Класс игрока
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.attack_damage = 20
        self.attack_cooldown = 0
        self.parry_cooldown = 0
        self.attack_radius = math.sqrt(self.width**2 + self.height**2) * 1.5
        self.parry_radius = math.sqrt(self.width**2 + self.height**2) * 1.5
        self.parry_active = False
        self.parry_duration = 0
        self.direction = 1  # 1 - вправо, -1 - влево
        self.is_moving = False
        self.is_attacking = False
        self.is_parrying = False
        
        # Анимации игрока
        self.stand_anim = Animation("player-stand", 1)
        self.walk_anim = Animation("player-walk", 3)
        self.attack_anim = Animation("player-attack", 3, loop=False)
        self.parry_anim = Animation("player-parry", 5, loop=False)
        
        # Текущая анимация
        self.current_anim = self.stand_anim
    
    def move(self, dx, dy, walls):
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Обновляем направление игрока
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1
        
        # Проверка столкновений со стенами
        player_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        for wall in walls:
            if player_rect.colliderect(wall.rect):
                return False
        
        # Проверка границ экрана
        if 0 <= new_x <= WIDTH - self.width and 0 <= new_y <= HEIGHT - self.height:
            self.x = new_x
            self.y = new_y
            self.is_moving = True
            return True
        
        self.is_moving = False
        return False

    def attack(self, enemies):
        if self.attack_cooldown <= 0:
            attack_sound.play()
            for enemy in enemies:
                distance = math.sqrt((self.x - enemy.x)**2 + (self.y - enemy.y)**2)
                if distance <= self.attack_radius:
                    enemy.health -= self.attack_damage
                    enemy_hit_sound.play()
            self.attack_cooldown = 0.5 * 60  # 0.5 секунды (60 FPS)
            self.is_attacking = True
            self.attack_anim.reset()
            return True
        return False

    def parry(self, enemies, boss=None):
        if self.parry_cooldown <= 0:
            parry_sound.play()
            self.parry_active = True
            self.parry_duration = 3 * 60  # 3 секунды
            self.parry_cooldown = 1.5 * 60  # 1.5 секунды
            self.is_parrying = True
            self.parry_anim.reset()
            
            # Заморозка врагов в радиусе
            for enemy in enemies:
                distance = math.sqrt((self.x - enemy.x)**2 + (self.y - enemy.y)**2)
                if distance <= self.parry_radius:
                    enemy.is_parried = True
                    enemy.parry_duration = 3 * 60
            
            # Обработка пуль босса
            if boss and boss.bullets:
                for bullet in boss.bullets[:]:
                    distance = math.sqrt((self.x - bullet['x'])**2 + (self.y - bullet['y'])**2)
                    if distance <= self.parry_radius:
                        # Пуля летит обратно к боссу
                        bullet['dx'] = (boss.x - bullet['x']) / 10
                        bullet['dy'] = (boss.y - bullet['y']) / 10
                        bullet['is_parried'] = True
            return True
        return False

    def draw(self, screen):
        # Определяем текущую анимацию
        if self.is_parrying and not self.parry_anim.done:
            self.current_anim = self.parry_anim
        elif self.is_attacking and not self.attack_anim.done:
            self.current_anim = self.attack_anim
        elif self.is_moving:
            self.current_anim = self.walk_anim
        else:
            self.current_anim = self.stand_anim
        
        # Получаем текущий кадр анимации
        frame = self.current_anim.get_current_frame()
        
        # Отражаем спрайт, если игрок смотрит влево
        if self.direction == -1:
            frame = pygame.transform.flip(frame, True, False)
        
        # Рисуем спрайт
        screen.blit(frame, (self.x, self.y))
        
        # Полоска здоровья
        health_ratio = self.health / self.max_health
        health_width = self.width * health_ratio
        pygame.draw.rect(screen, RED, (self.x, self.y - 10, self.width, 5))
        pygame.draw.rect(screen, GREEN, (self.x, self.y - 10, health_width, 5))
        
        # Эффект парирования
        if self.parry_active:
            pygame.draw.circle(screen, YELLOW, 
                             (self.x + self.width//2, self.y + self.height//2), 
                             int(self.parry_radius), 2)

    def update(self):
        # Обновляем анимации
        self.stand_anim.update()
        self.walk_anim.update()
        self.attack_anim.update()
        self.parry_anim.update()
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        else:
            self.is_attacking = False
        
        if self.parry_cooldown > 0:
            self.parry_cooldown -= 1
        
        if self.parry_active:
            self.parry_duration -= 1
            if self.parry_duration <= 0:
                self.parry_active = False
                self.is_parrying = False
        
        self.is_moving = False

# Класс врага
class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.speed = 2
        self.health = 50
        self.max_health = 50
        self.attack_damage = 10
        self.attack_cooldown = 0
        self.is_parried = False
        self.parry_duration = 0
        self.direction = 1  # 1 - вправо, -1 - влево
        self.is_moving = False
        
        # Анимации врага
        self.stand_anim = Animation("enemy-stand", 1)
        self.walk_anim = Animation("enemy-walk-attack", 5)
        self.death_anim = Animation("enemy-death", 2, loop=False)
        
        # Текущая анимация
        self.current_anim = self.stand_anim
        self.is_alive = True

    def move_towards(self, player, walls):
        if self.is_parried or not self.is_alive:
            return False
        
        dx, dy = player.x - self.x, player.y - self.y
        distance = max(1, math.sqrt(dx**2 + dy**2))
        dx, dy = dx / distance * self.speed, dy / distance * self.speed
        
        # Обновляем направление врага
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1
        
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Проверка столкновений со стенами
        enemy_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        for wall in walls:
            if enemy_rect.colliderect(wall.rect):
                self.is_moving = False
                return False
        
        # Проверка границ экрана
        if 0 <= new_x <= WIDTH - self.width and 0 <= new_y <= HEIGHT - self.height:
            self.x = new_x
            self.y = new_y
            self.is_moving = True
            return True
        
        self.is_moving = False
        return False

    def attack(self, player):
        if self.attack_cooldown <= 0 and not self.is_parried and self.is_alive:
            player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
            enemy_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            if enemy_rect.colliderect(player_rect):
                player.health -= self.attack_damage
                player_hit_sound.play()
                self.attack_cooldown = 1.5 * 60  # 1.5 секунды
                return True
        return False

    def draw(self, screen):
        # Определяем текущую анимацию
        if not self.is_alive and not self.death_anim.done:
            self.current_anim = self.death_anim
        elif self.is_parried:
            self.current_anim = self.stand_anim
        elif self.is_moving:
            self.current_anim = self.walk_anim
        else:
            self.current_anim = self.stand_anim
        
        # Получаем текущий кадр анимации
        frame = self.current_anim.get_current_frame()
        
        # Отражаем спрайт, если враг смотрит влево
        if self.direction == -1:
            frame = pygame.transform.flip(frame, True, False)
        
        # Рисуем спрайт
        screen.blit(frame, (self.x, self.y))
        
        # Полоска здоровья (только если враг жив)
        if self.is_alive:
            health_ratio = self.health / self.max_health
            health_width = self.width * health_ratio
            pygame.draw.rect(screen, RED, (self.x, self.y - 10, self.width, 5))
            pygame.draw.rect(screen, GREEN, (self.x, self.y - 10, health_width, 5))
        
        # Эффект парирования
        if self.is_parried:
            pygame.draw.circle(screen, YELLOW, 
                             (self.x + self.width//2, self.y + self.height//2), 
                             20, 2)

    def update(self):
        # Обновляем анимации
        self.stand_anim.update()
        self.walk_anim.update()
        self.death_anim.update()
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        if self.is_parried:
            self.parry_duration -= 1
            if self.parry_duration <= 0:
                self.is_parried = False
        
        if self.health <= 0 and self.is_alive:
            self.is_alive = False
            self.death_anim.reset()
        
        self.is_moving = False

# Класс босса
class Boss:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 50
        self.speed = 3
        self.health = 300
        self.max_health = 300
        self.attack_damage = 0.2  # 20% от здоровья игрока
        self.shoot_cooldown = 0
        self.bullets = []
        self.bullet_speed = 5
        self.spawn_timer = 60  # Таймер появления (1 секунда анимации)
        self.is_spawning = True
        self.bullet_damage = 15  # Урон от пули босса
        self.direction = 1  # 1 - вправо, -1 - влево
        self.is_moving = False
        
        # Анимации босса
        self.stand_anim = Animation("boss-stand", 1)
        self.walk_anim = Animation("boss-walk-attack", 1)
        
        # Текущая анимация
        self.current_anim = self.stand_anim

    def move_towards(self, player, walls):
        if self.is_spawning:
            return False
            
        dx, dy = player.x - self.x, player.y - self.y
        distance = max(1, math.sqrt(dx**2 + dy**2))
        dx, dy = dx / distance * self.speed, dy / distance * self.speed
        
        # Обновляем направление босса
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1
        
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Проверка столкновений со стенами
        boss_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        for wall in walls:
            if boss_rect.colliderect(wall.rect):
                self.is_moving = False
                return False
        
        # Проверка границ экрана
        if 0 <= new_x <= WIDTH - self.width and 0 <= new_y <= HEIGHT - self.height:
            self.x = new_x
            self.y = new_y
            self.is_moving = True
            return True
        
        self.is_moving = False
        return False

    def shoot(self, player):
        if self.shoot_cooldown <= 0 and not self.is_spawning:
            boss_shoot_sound.play()
            dx, dy = player.x - self.x, player.y - self.y
            distance = max(1, math.sqrt(dx**2 + dy**2))
            dx, dy = dx / distance * self.bullet_speed, dy / distance * self.bullet_speed
            
            self.bullets.append({
                'x': self.x + self.width // 2,
                'y': self.y + self.height // 2,
                'dx': dx,
                'dy': dy,
                'radius': 5,
                'is_parried': False,
                'damage': self.bullet_damage
            })
            self.shoot_cooldown = 2 * 60  # 2 секунды

    def draw(self, screen):
        if self.is_spawning:
            # Анимация появления - пульсирующий круг
            radius = int(self.spawn_timer / 3) + 10
            pygame.draw.circle(screen, YELLOW, 
                             (self.x + self.width//2, self.y + self.height//2), 
                             radius, 3)
        else:
            # Определяем текущую анимацию
            if self.is_moving:
                self.current_anim = self.walk_anim
            else:
                self.current_anim = self.stand_anim
            
            # Получаем текущий кадр анимации
            frame = self.current_anim.get_current_frame()
            
            # Отражаем спрайт, если босс смотрит влево
            if self.direction == -1:
                frame = pygame.transform.flip(frame, True, False)
            
            # Рисуем спрайт
            screen.blit(frame, (self.x, self.y))
        
        # Полоска здоровья (только после появления)
        if not self.is_spawning:
            health_ratio = self.health / self.max_health
            health_width = self.width * health_ratio
            pygame.draw.rect(screen, RED, (self.x, self.y - 10, self.width, 5))
            pygame.draw.rect(screen, GREEN, (self.x, self.y - 10, health_width, 5))
        
        # Пули
        for bullet in self.bullets:
            color = BLUE if bullet['is_parried'] else RED
            pygame.draw.circle(screen, color, (int(bullet['x']), int(bullet['y'])), bullet['radius'])

    def update(self, player):
        # Обновляем анимации
        self.stand_anim.update()
        self.walk_anim.update()
        
        # Обработка появления
        if self.is_spawning:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.is_spawning = False
        
        if self.shoot_cooldown > 0 and not self.is_spawning:
            self.shoot_cooldown -= 1
        
        # Обновление пуль
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['dx']
            bullet['y'] += bullet['dy']
            
            # Проверка попадания в игрока
            if not bullet['is_parried']:
                distance = math.sqrt((bullet['x'] - player.x)**2 + (bullet['y'] - player.y)**2)
                if distance < player.width // 2 + bullet['radius']:
                    player.health -= bullet['damage']
                    player_hit_sound.play()
                    self.bullets.remove(bullet)
                    continue
            
            # Проверка попадания в босса (если пуля была парирована)
            if bullet['is_parried']:
                distance = math.sqrt((bullet['x'] - self.x)**2 + (bullet['y'] - self.y)**2)
                if distance < self.width // 2:
                    self.health -= 50  # Урон от возвращенной пули
                    enemy_hit_sound.play()
                    self.bullets.remove(bullet)
                    continue
            
            # Удаление пуль за пределами экрана
            if (bullet['x'] < 0 or bullet['x'] > WIDTH or 
                bullet['y'] < 0 or bullet['y'] > HEIGHT):
                self.bullets.remove(bullet)
        
        self.is_moving = False

# Класс стены
class Wall:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = GRAY

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)

# Функция создания случайной позиции
def get_random_position(width, height, walls, other_objects=[]):
    while True:
        x = random.randint(0, WIDTH - width)
        y = random.randint(0, HEIGHT - height)
        new_rect = pygame.Rect(x, y, width, height)
        
        # Проверка столкновений со стенами
        collision = False
        for wall in walls:
            if new_rect.colliderect(wall.rect):
                collision = True
                break
        
        # Проверка столкновений с другими объектами
        if not collision:
            for obj in other_objects:
                obj_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                if new_rect.colliderect(obj_rect):
                    collision = True
                    break
        
        if not collision:
            return x, y

# Функция создания уровня
def create_level(level, walls):
    player = None
    enemies = []
    boss = None
    
    # Создаем игрока
    player_x, player_y = get_random_position(30, 30, walls)
    player = Player(player_x, player_y)
    
    # Создаем врагов в зависимости от уровня
    num_enemies = 3 + level * 2
    for _ in range(num_enemies):
        enemy_x, enemy_y = get_random_position(30, 30, walls, [player])
        enemies.append(Enemy(enemy_x, enemy_y))
    
    return player, enemies, boss

# Функция отрисовки меню
def draw_menu(screen, game_state):
    screen.fill(BLACK)
    
    if game_state == "menu":
        title = title_font.render("ABOBIK", True, WHITE)
        new_game_text = font.render("Новая игра (N)", True, WHITE)
        exit_text = font.render("Выход (Q)", True, WHITE)
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        screen.blit(new_game_text, (WIDTH//2 - new_game_text.get_width()//2, HEIGHT//2))
        screen.blit(exit_text, (WIDTH//2 - exit_text.get_width()//2, HEIGHT//2 + 50))
    
    elif game_state == "game_over":
        title = title_font.render("Игра окончена", True, RED)
        restart_text = font.render("Начать заново (R)", True, WHITE)
        menu_text = font.render("В меню (M)", True, WHITE)
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2))
        screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, HEIGHT//2 + 50))
    
    elif game_state == "victory":
        title = title_font.render("Победа!", True, GREEN)
        next_level_text = font.render("Следующий уровень (N)", True, WHITE)
        menu_text = font.render("В меню (M)", True, WHITE)
        
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        screen.blit(next_level_text, (WIDTH//2 - next_level_text.get_width()//2, HEIGHT//2))
        screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, HEIGHT//2 + 50))
    
    pygame.display.flip()

# Основная функция игры
def main():
    global WIDTH, HEIGHT, screen
    
    clock = pygame.time.Clock()
    game_state = "menu"  # menu, game, game_over, victory
    level = 1
    
    # Создаем стены
    walls = [
        Wall(100, 100, 200, 20),
        Wall(400, 200, 20, 200),
        Wall(200, 400, 300, 20),
        Wall(500, 100, 20, 250),
        Wall(50, 300, 150, 20)
    ]
    
    player, enemies, boss = None, [], None
    fullscreen = False
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                
                if game_state == "menu":
                    if event.key == pygame.K_n:
                        player, enemies, boss = create_level(level, walls)
                        game_state = "game"
                    elif event.key == pygame.K_q:
                        running = False
                
                elif game_state == "game_over":
                    if event.key == pygame.K_r:
                        player, enemies, boss = create_level(level, walls)
                        game_state = "game"
                    elif event.key == pygame.K_m:
                        game_state = "menu"
                        level = 1
                
                elif game_state == "victory":
                    if event.key == pygame.K_n:
                        level += 1
                        player, enemies, boss = create_level(level, walls)
                        game_state = "game"
                    elif event.key == pygame.K_m:
                        game_state = "menu"
                        level = 1
        
        if game_state == "game":
            keys = pygame.key.get_pressed()
            
            # Управление игроком
            dx, dy = 0, 0
            if keys[pygame.K_w]:
                dy = -player.speed
            if keys[pygame.K_s]:
                dy = player.speed
            if keys[pygame.K_a]:
                dx = -player.speed
            if keys[pygame.K_d]:
                dx = player.speed
            
            if dx != 0 or dy != 0:
                player.move(dx, dy, walls)
            
            # Атака и парирование мышью
            mouse_buttons = pygame.mouse.get_pressed()
            if mouse_buttons[0]:  # ЛКМ - атака
                player.attack(enemies)
            
            if mouse_buttons[2]:  # ПКМ - парирование
                player.parry(enemies, boss)
            
            # Обновление игрока
            player.update()
            
            # Обновление врагов
            for enemy in enemies[:]:
                enemy.move_towards(player, walls)
                enemy.attack(player)
                enemy.update()
                
                # Удаление мертвых врагов и восстановление здоровья игрока
                if enemy.health <= 0 and enemy.death_anim.done:
                    player.health = min(player.max_health, player.health + int(0.2 * player.max_health))
                    enemies.remove(enemy)
            
            # Проверка появления босса
            if not enemies and not boss:
                boss_x, boss_y = get_random_position(50, 50, walls, [player])
                boss = Boss(boss_x, boss_y)
            
            # Обновление босса
            if boss:
                boss.move_towards(player, walls)
                boss.shoot(player)
                boss.update(player)
                
                # Проверка смерти босса
                if boss.health <= 0:
                    boss = None
                    game_state = "victory"
            
            # Проверка смерти игрока
            if player.health <= 0:
                game_state = "game_over"
            
            # Отрисовка
            screen.fill(BLACK)
            
            for wall in walls:
                wall.draw(screen)
            
            player.draw(screen)
            
            for enemy in enemies:
                enemy.draw(screen)
            
            if boss:
                boss.draw(screen)
            
            # Отображение информации
            level_text = font.render(f"Уровень: {level}", True, WHITE)
            screen.blit(level_text, (10, 10))
            
            health_text = font.render(f"Здоровье: {player.health}/{player.max_health}", True, WHITE)
            screen.blit(health_text, (10, 40))
            
            enemies_text = font.render(f"Врагов: {len(enemies)}", True, WHITE)
            screen.blit(enemies_text, (10, 70))
            
            if boss:
                boss_text = font.render("Босс!", True, ORANGE)
                screen.blit(boss_text, (10, 100))
            
            pygame.display.flip()
        
        elif game_state in ["menu", "game_over", "victory"]:
            draw_menu(screen, game_state)
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()