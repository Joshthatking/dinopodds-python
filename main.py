import pygame
import config
from game import Game

# pygame.init()

# screen = pygame.display.set_mode((640,480))

# pygame.display.set_caption("DinoPodds")

# game = game(screen)

# #Game Display Loop
# while True:
#     # screen.fill(config.BLACK)
#     game.update()
#     pygame.display.flip()

if __name__ == '__main__':
    game = Game()
    game.run()



