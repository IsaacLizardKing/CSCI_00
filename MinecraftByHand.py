import numpy as np
import cv2

# Relevant Block Codes: 

MC_AIR = 0x00
MC_STONE = 0x01
MC_GRASS = 0x02
MC_COBBLESTONE = 0x04
MC_STILL_LAVA = 0x0A
MC_RAIL = 0x42
MC_REDSTONE_ORE = 0x49
CUSTOM_GOAL = 0xFF

# Vague attempt at making block placing dynamic, makes it possible to place blocks in voxels with air or fluid in it
# while preventing block replacing
MC_BLOCK_PRIORITY_DICT = {}
MC_BLOCK_PRIORITY_DICT[MC_AIR] = 0
MC_BLOCK_PRIORITY_DICT[MC_STONE] = 2
MC_BLOCK_PRIORITY_DICT[MC_GRASS] = 2
MC_BLOCK_PRIORITY_DICT[MC_COBBLESTONE] = 2
MC_BLOCK_PRIORITY_DICT[MC_STILL_LAVA] = 1
MC_BLOCK_PRIORITY_DICT[MC_RAIL] = 0
MC_BLOCK_PRIORITY_DICT[MC_REDSTONE_ORE] = 2
MC_BLOCK_PRIORITY_DICT[CUSTOM_GOAL] = 3

# This is not so useful for the goals of the assignment, as alex doesn't
# need to place solid blocks. But if alex needed to say, build a wood 
# wall around the railway, then it would come of use If a block has a 
# hitbox, then it has a value of one (in this dict), if not, it has a 
# value of 0
MC_BLOCK_SPACE_OCCUPYING_DICT = {}
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_AIR] = 0
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_STONE] = 1
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_GRASS] = 1
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_COBBLESTONE] = 1
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_STILL_LAVA] = 0
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_RAIL] = 0
MC_BLOCK_SPACE_OCCUPYING_DICT[MC_REDSTONE_ORE] = 1
MC_BLOCK_SPACE_OCCUPYING_DICT[CUSTOM_GOAL] = 1

# This is purely for the purpose of rendering. I didn't want to go 
# through the trouble of making textures and then set up texture loading
# etc etc.
# Blue, Green, Red, Opacity
MC_BLOCK_COLORS = {}
MC_BLOCK_COLORS[MC_AIR] = 0x00000000
MC_BLOCK_COLORS[MC_STONE] = 0x808080FF
MC_BLOCK_COLORS[MC_GRASS] = 0x39DB5EFF
MC_BLOCK_COLORS[MC_COBBLESTONE] = 0x505050FF
MC_BLOCK_COLORS[MC_STILL_LAVA] = 0x0050F6FF
MC_BLOCK_COLORS[MC_RAIL] = 0x004B86FF
MC_BLOCK_COLORS[MC_REDSTONE_ORE] = 0x101050FF
MC_BLOCK_COLORS[CUSTOM_GOAL] = 0x19F1FCFF

# This is recreates the stage presented by the problem. it's not
# particularly elegant, mostly because the stage is very clearly
# set up without a coherent world generation procedure.
def InitWorld():
	World = np.zeros((16, 3, 11), np.uint8) 
	World[:, 0, :] = MC_GRASS # ground level is grass
	World[4:6, 0, :] = MC_STILL_LAVA # this creates the lava river
	X, Y = np.mgrid[:16, :11]
	AirMask = (Y == 8) * ((X == 6) + (X == 11)) + (Y == 5) + (Y == 6) * (X > 9) + (Y != 7) * (X == 11) + (Y == 2) * ((X == 6) + (X > 9)) 
	
	RedStoneMask = (Y == 6) * (X == 6) + (X == 8) * ((Y == 3) + (Y == 7)) + (Y == 8) * (X == 9) + (Y == 4) * (X == 10)
	# creates the somewhat circular stone shape
	World[6:12, 1, 2:9] = (MC_STONE * (1 - AirMask))[6:12, 2:9]
	# places the redstone
	World[:, 1, :] = World[:, 1, :] * (1 - RedStoneMask) + RedStoneMask * MC_REDSTONE_ORE
	
	# This next part randomly places lava underneath the stone/redstone
	StoneMask = (World[:, 1, :] == MC_STONE) + (World[:, 1, :] == MC_REDSTONE_ORE)
	RandMask = np.uint8(np.random.rand(16, 11) + 0.5) 
	World[:, 0, :] = ((RandMask[:, :] * StoneMask) == 0) * World[:, 0, :] + RandMask * StoneMask * MC_STILL_LAVA
	
	# places the goal
	World[13, 1:-1, 5] = CUSTOM_GOAL
	
	return World


def DisplayMap(time = 100):
	# converts the voxel map into color information
	MapCopy = np.zeros((16, 3, 11, 4), np.uint8)
	# iterate through all elements of the map
	for i in range(MapCopy.shape[0]):
		for j in range(MapCopy.shape[1]):
			for k in range(MapCopy.shape[2]):
				MapCopy[i, j, k, 0] = MC_BLOCK_COLORS[Map[i, j, k]] >> 24
				MapCopy[i, j, k, 1] = (MC_BLOCK_COLORS[Map[i, j, k]] >> 16) % 256
				MapCopy[i, j, k, 2] = (MC_BLOCK_COLORS[Map[i, j, k]] >> 8) % 256
				MapCopy[i, j, k, 3] = MC_BLOCK_COLORS[Map[i, j, k]] % 256
	# This is supposed to flatten the map in a very lazy and not 
	# reliable way. it breaks if there is a gap between blocks.
	# There was a better way to do this, but thankfully I don't have to
	# think about it.
	MapCopy[:, :-1, :, :3] = np.uint8(MapCopy[:, :-1, :, :3] * (1 - MapCopy[:, 1:, :, 3, None] / 255))
	Frame = MapCopy[:, 0, :, :3] + MapCopy[:, 1, :, :3] + MapCopy[:, 2, :, :3]
	
	# Make the tile alex is on white
	Frame[AlexCoords[0], AlexCoords[2], 0] = 0xFF
	Frame[AlexCoords[0], AlexCoords[2], 1] = 0xFF
	Frame[AlexCoords[0], AlexCoords[2], 2] = 0xFF
	# Make the tile in front of alex glow a little brighter.
	Frame[AlexCoords[0] + AlexDir[0], AlexCoords[2] + AlexDir[1], :] = np.uint8(Frame[AlexCoords[0] + AlexDir[0], AlexCoords[2] + AlexDir[1], :] * 0.6 + 255 * 0.4)
	# rotate the frame and show.
	cv2.imshow("image", cv2.rotate(Frame, cv2.ROTATE_90_COUNTERCLOCKWISE))
	cv2.waitKey(time)

Map = InitWorld()
AlexCoords = [1, 1, 5] # [x, y, z] (y is depth coordinate)
AlexDir = (1, 0) # [x, z] (Vectorized to facilitate interaction with coordinate system)
DisplayMap(0)

# direction vector illustrated:
# 
#           N (+1)
#           ▲
#           |
# (-1) W ◀— ◆ —▶ E (+1)
#           |
#           ▼
#      (-1) S
# 
# notice that every time we go from north-south to east-west, the sign
# changes, and every time we go from east-west to north-south, the sign
# does not change. this makes changing the direction vector very simple.

def RotateLeft():
	global AlexDir
	AlexDir = (-AlexDir[1], AlexDir[0])

def RotateRight():
	global AlexDir
	AlexDir = (AlexDir[1], -AlexDir[0])

def MoveForward():
	global AlexCoords
	# If block ahead of alex does not occupy space
	if(MC_BLOCK_SPACE_OCCUPYING_DICT[Map[AlexCoords[0] + AlexDir[0], AlexCoords[1], AlexCoords[2] + AlexDir[1]]] == 0):
		# Then move alex forward
		AlexCoords = [AlexCoords[0] + AlexDir[0], AlexCoords[1], AlexCoords[2] + AlexDir[1]]
	# I should check if the block below alex is solid, and if the block
	# in front of alex's head is solid, but it's not necessary
	

def PlaceBlock(BlockCode):
	global Map, AlexCoords
	# place block
	Map[AlexCoords[0], AlexCoords[1], AlexCoords[2]] = BlockCode
	# if block placed occupies space
	if(MC_BLOCK_SPACE_OCCUPYING_DICT[Map[AlexCoords[0], AlexCoords[1], AlexCoords[2]]] == 1):
		# then make alex jump
		AlexCoords[1] += 1

def PlaceBlockAhead(BlockCode):
	global Map
	# If the block ahead has a lower priority than the given block
	if(MC_BLOCK_PRIORITY_DICT[Map[AlexCoords[0] + AlexDir[0], AlexCoords[1] - 1, AlexCoords[2] + AlexDir[1]]] < MC_BLOCK_PRIORITY_DICT[BlockCode]):
		# then place the gosh darn block
		Map[AlexCoords[0] + AlexDir[0], AlexCoords[1] - 1, AlexCoords[2] + AlexDir[1]] = BlockCode

def MineBlock():
	global Map
	# set the block ahead of alex to air
	Map[AlexCoords[0] + AlexDir[0], AlexCoords[1], AlexCoords[2] + AlexDir[1]] = 0x00

#
# ======================================================================
# ||||           STUFF THAT IS RELEVANT TO THE ASSIGNMENT           ||||
# ======================================================================
#

# Alex's commands:
# 
# Rotate Left   ->    L
# Rotate Right  ->    R
# Move Forward  ->    F
# Mine          ->    M
# Place Track   ->    T

commandstr = list("TFTFTFTFTFTLMRFTFTLMFMRRFMFMLLFRFTFTRMLFTFTLF")
for act in commandstr:
	if(act == 'L'):
		RotateLeft()
	elif(act == 'R'):
		RotateRight()
	elif(act == 'F'):
		# I figured this was alright
		if(Map[AlexCoords[0] + AlexDir[0], AlexCoords[1] - 1, AlexCoords[2] + AlexDir[1]] == MC_STILL_LAVA):
			PlaceBlockAhead(MC_COBBLESTONE)
			DisplayMap()
		MoveForward()
		DisplayMap()
	elif(act == 'M'):
		MineBlock()
		DisplayMap()
	elif(act == 'P'):
		PlaceBlock(MC_COBBLESTONE)
		DisplayMap()
	elif(act == 'T'):
		PlaceBlock(MC_RAIL)
		DisplayMap()

DisplayMap(0)
