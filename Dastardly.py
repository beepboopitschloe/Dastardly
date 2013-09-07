#Dastardly
#A game of style, subterfuge, and superweapons.
#Dastardly Pre-Alpha v.24
#(c) Noah Muth 2013

import libtcodpy as libtcod
import dastardly_colors as colors
import textwrap
import math
import time

########
#CLASSES
########

#Map Classes

class Tile:
	def __init__(self, blocked, x, y):
		self.blocked = blocked
		self.color = libtcod.dark_green
		self.x = x
		self.y = y
		self.is_street = False
		self.is_building = False
		self.is_in_building = False
		self.is_door = False
		self.is_air = False
		self.char = None
		self.contents = []

class Map:
	def __init__(self, name, width, height):
		self.name = name
		self.type = 'map'
		self.blocks = False
		self.on_travel_map = True
		self.width = width
		self.height = height
		self.owner = None
		#Set up the map array. Nested list comprehensions AGH
		self.map = [[Tile(False, x, y) for y in range(height)] for x in range(width)]
		
		self.inhabitant = None
		
		#Set up the lists of actors and items within the map.
		self.actors = []
		self.items = []
		self.effects = []
		self.events = []
		self.total_threat = 0
		
		#Coordinates on the Travel map.
		self.travel_x = 0
		self.travel_y = 0
		self.on_travel_map = False
		
		self.con = libtcod.console_new(width, height)
	
	def update_events(self):
		for event in self.events:
			#print event.subject.name, event.verb.name, event.object.name
			event.age += 1
			if event.age > 30:
				self.events.remove(event)
	
	def add_event(self, subject, verb, object):
		self.events.append(Event(subject, verb, object))

class Rect:
	def __init__(self, x, y, w, h):
		self.x = x
		self.y = y
		self.w = w
		self.h = h
	
	def block_hollow_rect(self, map, block):
		draw_x = self.x
		draw_y = self.y
		for x in range(self.w):
			map[draw_x][self.y].blocked = block
			map[draw_x][self.y+self.h].blocked = block
			draw_x += 1
		for y in range(self.h):
			map[self.x][draw_y].blocked = block
			map[self.x+self.w][draw_y].blocked = block
			draw_y += 1
		map[draw_x][draw_y].blocked = block
	
	def color_hollow_rect(self, map, color):
		draw_x = self.x
		draw_y = self.y
		for x in range(self.w):
			map[draw_x][self.y].color = color
			map[draw_x][self.y+self.h].color = color
			draw_x += 1
		for y in range(self.h):
			map[self.x][draw_y].color = color
			map[self.x+self.w][draw_y].color = color
			draw_y += 1
		map[draw_x][draw_y].color = color

class Building(Rect):
	def __init__(self, x, y, w, h, tiles):
		self.x = x
		self.y = y
		self.w = w
		self.h = h
		self.tiles = tiles
		self.claimed = False
		self.link = None

class Place:
	def __init__(self, name, total_size, building_size, floors, spawn_rate, specials):
		self.name = name
		self.total_size = total_size
		self.building_size = building_size
		self.building_x = total_size/2-building_size/2-1
		self.building_y = total_size/2-building_size/2-1
		self.num_floors = floors
		self.spawn_rate = spawn_rate
		self.spawn_ai = 'random_move'
		self.specials = specials
		self.shop = None
		print self.specials
		if self.specials.count('queue') != 0:
			self.specials.append(self.specials.pop(self.specials.index('queue')))
			print self.specials
			print 'trollface'
		
		self.timer = 0
		if self.spawn_rate != 0:
			self.spawn_alarm = LIMIT_FPS*60/self.spawn_rate
		else:
			self.spawn_alarm = 0
		
		self.floors = []
		
		self.generate()
		
	def generate(self):
		for k in range(self.num_floors):
			self.floors.append(Map(self.name, self.total_size, self.total_size))
			self.floors[k].owner = self
			print self.name+'F'+str(k+1)+'_map'
			if k == 0:
				#Draw the building rectangle.
				self.building = Rect(self.building_x, self.building_y, self.building_size, self.building_size)
				self.building.block_hollow_rect(self.floors[k].map, True)
				self.building.color_hollow_rect(self.floors[k].map, colors.building)
				
				#Add the door. Only on F1, of course!
				self.doorx = libtcod.random_get_int(0, self.building_x+2, self.building_x+self.building_size-2)
				self.floors[k].map[self.doorx][self.building.y+self.building.h].blocked = False
				self.floors[k].map[self.doorx][self.building.y+self.building.h].color = colors.door
				self.doory = self.building.y+self.building.h
				
				#And now the stairs.
				if self.num_floors > 1:
					if self.specials.count('stairwell') == 0:
						self.floors[k].actors.append(Furniture('stairs up', libtcod.random_get_int(0, self.building_x+1, self.building_x+self.building_size-1),
												libtcod.random_get_int(0, self.building_y+1, self.building_y+self.building_size/2),
												libtcod.dark_orange, '<'))
					else:
						self.floors[k].actors.append(Furniture('stairs up', self.doorx - 1, self.building_y + self.building_size-1,
												libtcod.dark_orange, '<'))
						build_x = self.doorx-2
						build_y = self.building_y + self.building_size-1
						self.floors[k].map[build_x][build_y].blocked = True
						self.floors[k].map[build_x][build_y].color = colors.building
						build_y -= 1
						for x in range(5):
							if build_x != self.doorx:
								self.floors[k].map[build_x][build_y].blocked = True
								self.floors[k].map[build_x][build_y].color = colors.building
							else:
								self.floors[k].map[build_x][build_y].color = colors.door
							build_x += 1
						self.floors[k].map[build_x-1][build_y+1].blocked = True
						self.floors[k].map[build_x-1][build_y+1].color = colors.building
				
				#Set the tile colors.
				for x in range(self.total_size):
					for y in range(self.total_size):
						if x > self.building.x and x < self.building.x+self.building.w and y > self.building.y and y < self.building.y+self.building.h:
							if self.floors[k].map[x][y].blocked == False:
								self.floors[k].map[x][y].color = colors.floor
				
				#Now, run the generation for any specials the place has.
				for special in self.specials:
					self.generate_special(self.floors[k], special)
				#Scatter gold!
				for x in range(10):
					self.floors[k].items.append(Item('gold', libtcod.random_get_int(0, self.building_x+1, self.building_x+self.building_size-1),
											libtcod.random_get_int(0, self.building_y+1, self.building_y+self.building_size/2),
											libtcod.dark_yellow, 'g'))
				
				#Add to the maps list- only the first floor, so it will link to the outside.
				maps.append(self.floors[k])
			
			else:
				#Instead of ground tiles, make them air tiles.
				for x in range(self.total_size):
					for y in range(self.total_size):
						self.floors[k].map[x][y].color = colors.air
				#Draw the building rectangle.
				self.building = Rect(self.building_x, self.building_y, self.building_size, self.building_size)
				self.building.block_hollow_rect(self.floors[k].map, True)
				self.building.color_hollow_rect(self.floors[k].map, colors.building)
				#Fill the building rectangle with floor tiles instead of ground tiles.
				for x in range(self.total_size):
					for y in range(self.total_size):
						if x > self.building.x and x < self.building.x + self.building.w and y > self.building.y and y < self.building.y + self.building.h:
							self.floors[k].map[x][y].color = colors.floor
				#And now the stairs.
				if k+1 < self.num_floors:
					if self.specials.count('stairwell') == 0:
						self.floors[k].actors.append(Furniture('stairs up', libtcod.random_get_int(0, self.building_x+1, self.building_x+self.building_size-1),
												libtcod.random_get_int(0, self.building_y+1, self.building_y+self.building_size/2),
												libtcod.dark_orange, '<'))
					else:
						if k%2 == 1:
							self.floors[k].actors.append(Furniture('stairs up', self.doorx + 1, self.building_y + self.building_size-1,
												libtcod.dark_orange, '<'))
						else:
							self.floors[k].actors.append(Furniture('stairs up', self.doorx - 1, self.building_y + self.building_size-1,
												libtcod.dark_orange, '<'))
						build_x = self.doorx-2
						build_y = self.building_y + self.building_size-1
						self.floors[k].map[build_x][build_y].blocked = True
						self.floors[k].map[build_x][build_y].color = colors.building
						build_y -= 1
						for x in range(5):
							if build_x != self.doorx:
								self.floors[k].map[build_x][build_y].blocked = True
								self.floors[k].map[build_x][build_y].color = colors.building
							else:
								self.floors[k].map[build_x][build_y].color = colors.door
							build_x += 1
						self.floors[k].map[build_x-1][build_y+1].blocked = True
						self.floors[k].map[build_x-1][build_y+1].color = colors.building
				self.floors[k].actors.append(Furniture('stairs down', libtcod.random_get_int(0, self.building_x+1, self.building_x+self.building_size-1),
											libtcod.random_get_int(0, self.building_y+1, self.building_y+self.building_size/2),
											libtcod.dark_orange, '>'))
				for actor in self.floors[k-1].actors:
					if actor.name == 'stairs up':
						self.floors[k].actors[len(self.floors[k].actors)-1].x = actor.x
						self.floors[k].actors[len(self.floors[k].actors)-1].y = actor.y
	
	def generate_special(self, map, special):
		if special == 'shop_counter':
			for build_x in range(2*self.building_size/3):
				build_x += 1
				map.map[self.building.x+build_x][self.building.y+self.building_size/4].blocked = True
				map.map[self.building.x+build_x][self.building.y+self.building_size/4].color = colors.counter
		elif special == 'checkered_floor':
			for x in range(self.building_size):
				for y in range(self.building_size):
					if map.map[self.building.x+x][self.building.y+y].color == colors.floor:
						if x != 0 and y != 0:
							if y%2 == 0:
								if x%2 != 0:
									map.map[self.building.x+x][self.building.y+y].color = libtcod.grey+libtcod.light_grey*.5
							else:
								if x%2 == 0:
									map.map[self.building.x+x][self.building.y+y].color = libtcod.grey+libtcod.light_grey*.5
		elif special == 'queue':
			map.queue_x = self.total_size/2
			map.queue_y = self.building_y + self.building_size/4
			while map.map[map.queue_x][map.queue_y].blocked == True:
				map.queue_y += 1
			self.spawn_ai = 'queue'
		elif special == 'shopkeeper':
			self.shop = Shop(self)
			print 'doneskies.'

	def spawn_logic(self, floor = None):
		if self.timer < self.spawn_alarm:
			self.timer += 1
		elif self.timer == self.spawn_alarm and self.spawn_alarm != 0:
			if self.spawn_ai == 'random_move':
				new = create_agent(self.doorx, self.total_size-1)
				new.plug_ai(Random_Move_AI())
			elif self.spawn_ai == 'queue' and len(active_map.actors) < 8:
				new = create_agent(self.doorx, self.total_size-1)
				new.plug_ai(Queue_AI())
			self.timer = 0
		if floor != None:
			if floor.inhabitant != None:
				if libtcod.random_get_int(0, 1, 100) > 90:
					floor.inhabitant.spawn(15, 15)

#Actor Classes

class Actor:
	def __init__(self, name, gender, x, y, color, char, body):
		self.x = x
		self.y = y
		self.color = color
		self.char = char
		
		self.name = name
		self.gender = gender
		self.is_player = False
		self.body = body
		self.body.owner = self
		self.blocks = True
		self.threat_level = 0
		
		self.frontal_cortex = Frontal_Cortex(self)
		self.ai = None
		self.fighter = None
		self.type = 'actor'
		self.abstract = None
		self.bank = Bank(self)
		self.weapon = None
		
		self.conversation_partner = None
		self.conversation_string = 'Hello, my name is ' + self.name + '.'
		self.opinion_dict = {self.name : 10}
		for actor in active_map.actors:
			if actor.type == 'actor':
				self.opinion_dict[actor.name] = 0
				actor.opinion_dict[self.name] = 0
		
		self.set_attributes()
		
		self.setup_abilities()
		
		self.setup_inventory()
	
	def change_threat_level(self, amount):
		self.threat_level += amount
		if active_map != travelmap:
			active_map.total_threat += amount
		print self.name, self.threat_level
	
	def change_opinion(self, actor, dop):
		if self != player:
			original_opinion = self.opinion_dict[actor.name]
			self.opinion_dict[actor.name] += dop
		
			if self.opinion_dict[actor.name] >= 0:
				self.conversation_string = actor.name + ' is decent.'
			elif self.opinion_dict[actor.name] >= -5:
				self.conversation_string = 'I don\'t like ' + actor.name + '.'
			elif self.opinion_dict[actor.name] < -5:
				self.conversation_string = 'Die, ' + actor.name + '!'
				
				#** v.24 **
				#this statement prevents actors declaring their hostility
				#every time their AI changes.
				if original_opinion >= -5:
					message(self.name + ' has become hostile to ' + actor.name + "!", libtcod.yellow)

				if self.ai != None:
					if self.ai.type != 'beeline_attack_ai':
						self.plug_ai(Beeline_Attack_AI(actor))
	
	def setup_inventory(self):
		self.inv_dict = {}
		for part in self.body.parts:
			self.inv_dict[part.name] = part.item
		self.abstract_inv = []
	
	def set_attributes(self, att_dict = {'Athleticism' : 40, 'Muscle' : 40, 'Grace' : 40, 'Charm' : 40, 'Brains' : 40}):
		if len(att_dict) == 5:
			self.attributes = att_dict
			self.setup_description()
			self.change_threat_level(self.attributes['Muscle']/2)
	
	def setup_abilities(self):
		self.abilities = []
		if self.attributes['Charm'] > 20:
			self.abilities.append(Ability('fireball', 'projectile', 5))
	
	def setup_description(self):
		desc_dict = {'name' : self.name, 'gender' : self.gender, 'species' : self.body.name}
		self.description = []
		
		if self.gender == 'female':
			pronouns = {'pos' : 'her', 'ref' : 'her', 'sub' : 'she'}
		else:
			pronouns = {'pos' : 'his', 'ref' : 'him', 'sub' : 'he'}
		
		for item in desc_dict:
			self.description.append(pronouns['pos'].capitalize()  + ' ' + item + ' is ' + desc_dict[item] + '.')
		
		for att in self.attributes:
			if self.attributes[att] <= 35:
				self.description.append(pronouns['sub'].capitalize() + ' does not have much ' + att.lower() + '.')
			elif self.attributes[att] >= 50:
				self.description.append(pronouns['sub'].capitalize()  + ' has remarkable ' + att.lower() + '.')
			else:
				self.description.append(pronouns['pos'].capitalize()  + ' ' + att.lower() + ' is average.')
	
	def process_phrase(self, phrase):
		global conv_topic
		pass;
	
	def pick_up(self):
		tile = active_map.map[self.x][self.y]
		if len(tile.contents) > 1:
			bx = 0
			while tile.contents[bx].type == 'actor' or tile.contents[bx].type == 'furniture' or tile.contents[bx].type == 'cursor':
				bx += 1
				if bx == len(tile.contents):
					break
			pickup_successful = False
			if bx <= len(tile.contents)-1:
				target_item = tile.contents[bx]
				for part in self.body.parts:
					if part.type == 'limb':
						if part.flags['grasps'] == True and part.item == None:
							part.item = target_item
							message(self.name + ' picks up the ' + part.item.name + ' with their ' + part.name + '.', libtcod.dark_yellow)
							part.item.exit_tile()
							active_map.items.remove(part.item)
							self.weapon = part.item
							self.change_threat_level((self.weapon.damage_concentration + self.weapon.damage_reverb)/2)
							pickup_successful = True
							active_map.add_event(self, verbs['picks_up'], target_item)
							break
				if pickup_successful == False:
					#message("You don't have a free grasp.")
					player.abstract_inv.append(target_item)
					target_item.exit_tile()
					active_map.items.remove(target_item)
					message('You put the ' + target_item.name + ' in your satchel.')
					active_map.add_event(self, verbs['picks_up'], target_item)
			else:
				message("There's nothing here to pick up.")
		else:
			message("There's nothing here to pick up.")
	
	def drop(self, item):
		for part in self.body.parts:
			if part.item == item:
				item.x = self.x
				item.y = self.y
				active_map.map[self.x][self.y].contents.append(item)
				active_map.items.append(item)
				part.item = None
				if item == self.weapon:
					self.change_threat_level((self.weapon.damage_concentration + self.weapon.damage_reverb)/2)
					self.weapon = None
				break
		for k in self.abstract_inv:
			if k == item:
				item.x = self.x
				item.y = self.y
				active_map.map[self.x][self.y].contents.append(item)
				active_map.items.append(item)
				self.abstract_inv.remove(item)
				break
	
	def move_towards(self, target_x, target_y):
		#Vector to target, distance.
		#Subtract self.(x,y) from target_(x,y) to get the vector which determines the translation vector to get to the target (dx, dy).
		dx = target_x - self.x
		dy = target_y - self.y
		#Using dx and dy as sides of a right triangle, then the length of the translation vector is the hypotenuse. Pythagorean theorem! (dx ** 2 = dx^2)
		distance = math.sqrt(dx ** 2 + dy ** 2)
		
		#Normalize it to one tile (preserve direction), then round and convert to int
		#Divide the translation vector by the distance vector.
		if distance != 0:
			dx = int(round(dx/distance))
			dy = int(round(dy/distance))
		else:
			dx = 0
			dy = 0
		self.move(dx, dy)
	
	def move_away(self, target_x, target_y):
		#Vector to target, distance.
		#Subtract self.(x,y) from target_(x,y) to get the vector which determines the translation vector to get to the target (dx, dy).
		dx = target_x - self.x
		dy = target_y - self.y
		#Using dx and dy as sides of a right triangle, then the length of the translation vector is the hypotenuse. Pythagorean theorem! (dx ** 2 = dx^2)
		distance = math.sqrt(dx ** 2 + dy ** 2)
		
		#Normalize it to one tile (preserve direction), then round and convert to int
		#Divide the translation vector by the distance vector.
		if distance != 0:
			dx = int(round(dx/distance))
			dy = int(round(dy/distance))
		else:
			dx = 0
			dy = 0
		#Now make it the opposite. Imperfect, but it works for now.
		dx *= -1
		dy *= -1
		if self.x + dx < 0 or self.y + dy < 0 or self.x + dx >= active_map.width or self.y + dy >= active_map.height:
			message(self.name + ' has fled the area!', libtcod.yellow)
			self.exit_map()
		else:
			self.move(dx, dy)
	
	def move(self, dx, dy):
		global game_state
		#Moves the actor. Duh. Also resets the contents of its tile, before the move.
		#And handles attacking.
		active_map.map[self.x][self.y].contents.remove(self)
		if self.x+dx < active_map.width and self.y+dy < active_map.height:
			for k in active_map.map[self.x+dx][self.y+dy].contents:
				if k.type == 'actor':
					if k.fighter is not None and self.fighter is not None:
						self.fighter.attack(k)
		if not is_blocked(self.x + dx, self.y + dy):
			self.x += dx
			self.y += dy
	
	def draw(self):
		#Renders the actor on the active map console. Also, since it gets called every turn, updates the map with its position.
		libtcod.console_set_foreground_color(active_map.con, self.color)
		libtcod.console_put_char(active_map.con, self.x, self.y, self.char, libtcod.BKGND_SET)
		
		if active_map.map[self.x][self.y].contents.count(self) == 0:
			active_map.map[self.x][self.y].contents.append(self)
	
	def exit_tile(self):
		if active_map.map[self.x][self.y].contents.count(self) != 0:
			active_map.map[self.x][self.y].contents.remove(self)
	
	def switch_map(self, newmap, new_x, new_y):
		global active_map
		if active_map.actors.count(self) > 0:
			active_map.actors.remove(self)
		self.exit_tile()
		if self.is_player:
			active_map = newmap
			panels[4] = active_map.con
			if newmap.owner != None:
				if newmap.owner.shop != None:
					if newmap.owner.shop.shopkeeper == None:
						newmap.owner.shop.create_shopkeeper()
		self.x = new_x
		self.y = new_y
		newmap.actors.append(self)
	
	def exit_map(self):
		if active_map.actors.count(self) > 0:
			active_map.actors.remove(self)
		self.exit_tile()
	
	def enter_tile(self):
		if active_map.map[self.x][self.y].contents.count(self) == 0:
			active_map.map[self.x][self.y].contents.append(self)
	
	def plug_ai(self, ai):
		#Gives an AI to the actor, and lets the AI know who it's controlling.
		self.ai = ai
		self.ai.owner = self
	
	def plug_fighter(self, fighter):
		#Allows the actor to fight.
		self.fighter = fighter
		self.fighter.max_hp = self.body.total_hp/2
		self.fighter.hp = self.fighter.max_hp
		self.fighter.owner = self

class Cursor(Actor):
	def __init__(self, x, y, color, char = 'X'):
		self.x = x
		self.y = y
		self.color = color
		self.char = char
		self.blocks = False
		self.type = 'cursor'
		
	def move(self, dx, dy):
		#Cursors move like actors, only without the restrictions.
		if self.x + dx > 0 and self.x + dx < libtcod.console_get_width(active_map.con):
			self.x += dx
		if self.y + dy > 0 and self.y + dy < libtcod.console_get_height(active_map.con):
			self.y += dy
	
	def describe(self):
		#Get a description string from underneath the cursor.
		self.desc_string = ''
		if active_map.map[self.x][self.y].blocked:
			self.desc_string = 'Wall'
		else:
			self.desc_string = 'Floor'
		
		for k in active_map.map[self.x][self.y].contents:
			if k != self:
				if len(textwrap.wrap(self.desc_string + ', ' + k.name, libtcod.console_get_width(panel2)-2)) <= 1:
					self.desc_string = self.desc_string + ', ' + k.name
				else:
					self.desc_string = self.desc_string + '... '
					break
		

		#And print it to the message board.
		libtcod.console_set_foreground_color(panel2, libtcod.light_grey)
		libtcod.console_print_left(panel2, 2, 2, libtcod.BKGND_NONE, self.desc_string)

class Furniture(Actor):
	def __init__(self, name, x, y, color, char):
		self.x = x
		self.y = y
		self.color = color
		self.char = char
		self.name = name
		self.blocks = False
		self.type = 'furniture'
		self.ai = None
		self.fighter = None
		self.description = ['This is a ' + self.name + '.']

#Effects Classes

class Particle(Cursor):
	def __init__(self, x, y, color, effect, split_timer, split_num, opacity):
		self.x = x
		self.y = y
		self.type = 'particle'
		self.blocks = False
		self.color = color
		self.effect = effect
		self.split_timer_max = split_timer
		self.split_timer = self.split_timer_max
		self.split_num = split_num
		self.split_ready = False
		self.move_timer_max = 10
		self.move_timer = self.move_timer_max
		self.move_ready = False
		self.life_timer_max = libtcod.random_get_int(0, self.move_timer_max*10, self.move_timer_max*20)
		self.life_timer = self.life_timer_max
		self.opacity = opacity
	
	def update(self):
		if self.split_timer > 0:
			self.split_timer -= 1
		elif self.split_timer <= 0:
			self.split_ready = True
		if self.move_timer > 0:
			self.move_timer -= 1
		elif self.move_timer <= 0:
			self.move_ready = True
		if self.life_timer > 0:
			self.life_timer -= 1
		elif self.life_timer == 0:
			self.effect.particles.remove(self)
	
	def draw(self):
		#Renders the particle on the active map console. Also, since it gets called every turn, updates the map with its position.
		libtcod.console_set_back(active_map.con, self.x, self.y, self.color, libtcod.BKGND_SET)
		
		if active_map.map[self.x][self.y].contents.count(self) == 0:
			active_map.map[self.x][self.y].contents.append(self)
	
	def split(self, dx_min, dx_max, dy_min, dy_max):
		for i in range(self.split_num):
			new_x = -1
			new_y = -1
			if self.effect.effect_info['velocity'][0] != 0 and self.effect.effect_info['velocity'][1] == 0:
				#If the vector is horizontal, place no restrictions on x-dither.
				while new_x < 0 or new_x > active_map.width-1:
					new_x = self.x + libtcod.random_get_int(0, dx_min, dx_max)
				while new_y < 0 or new_y > active_map.height-1 or new_y < self.effect.y_core-1 or new_y > self.effect.y_core+1:
					new_y = self.y + libtcod.random_get_int(0, dy_min, dy_max)
			elif self.effect.effect_info['velocity'][1] != 0 and self.effect.effect_info['velocity'][0] == 0:
				#If it's vertical, place no restrictions on y-dither.
				while new_x < 0 or new_x > active_map.width-1 or new_x < self.effect.x_core-1 or new_x > self.effect.x_core+1:
					new_x = self.x + libtcod.random_get_int(0, dx_min, dx_max)
				while new_y < 0 or new_y > active_map.height-1:
					new_y = self.y + libtcod.random_get_int(0, dy_min, dy_max)
			else:
				#If it's diagonal, no restrictions at all! This makes diagonal projectiles a bit wonky, but meh.
				while new_x < 0 or new_x > active_map.width-1:
					new_x = self.x + libtcod.random_get_int(0, dx_min, dx_max)
				while new_y < 0 or new_y > active_map.height-1:
					new_y = self.y + libtcod.random_get_int(0, dy_min, dy_max)
			new = Particle(new_x, new_y, self.color, self.effect, self.split_timer_max, int(self.split_num/2), self.opacity)
			new.life_timer_max = self.life_timer_max/3 * 2
			new.life_timer = new.life_timer_max
			self.effect.particles.append(new)
		self.effect.particles.remove(self)

class Visual_Effect:
	def __init__(self, color, split_timer, split_num, opacity, effect_info = {'type' : 'projectile', 'velocity' : (1, 0)}):
		self.particles = [Particle(0, 0, color, self, split_timer, split_num, opacity)]
		self.effect_info = effect_info
		if effect_info['type'] == 'projectile':
			self.effect_logic = self.projectile_logic
		elif effect_info['type'] == 'explosion':
			self.effect_logic = self.explosion_logic
		self.activated = False
	
	def set_effects(self, effects = {'damage' : 4}):
		self.effects = effects
	
	def activate_toggle(self, x = 0, y = 0, velocity = (1, 0)):
		if self.activated == False:
			self.activated = True
			active_map.effects.append(self)
		else:
			self.activated == False
			active_map.effects.remove(self)
		self.x_core = x
		self.y_core = y
		self.effect_info['velocity'] = velocity

	def projectile_logic(self):
		#The projectile travels in its direction vector until it hits something.
		for particle in self.particles:
			particle.update()
		dx = self.effect_info['velocity'][0]
		dy = self.effect_info['velocity'][1]
		for particle in self.particles:
			if particle.move_ready == True:
				particle.move(dx, dy)
				particle.move_timer = particle.move_timer_max
				particle.move_ready = False
			if particle.split_ready == True:
				particle.split(dx-1, dx+1, dy-1, dy+1)
				particle.split_timer = particle.split_timer_max
				particle.split_ready = False
	
	def explosion_logic(self):
		for particle in self.particles:
			particle.update()

#Intelligence & Logic Classes (Locomotive Brain)

class Fighter:
	def __init__(self, actor):
		self.owner = actor
		
		self.max_hp = self.owner.body.total_hp/4 + self.owner.attributes['Muscle']/2
		self.hp = self.max_hp
		
		self.power = self.owner.attributes['Muscle']/2 + self.owner.attributes['Athleticism']/3 + self.owner.attributes['Grace']/4
		
		self.defense = (self.owner.attributes['Athleticism']/2 + self.owner.attributes['Grace']/3 + self.owner.attributes['Muscle']/4)/3 * 2
	
	def setup_attributes(self):
		self.power = self.owner.attributes['Muscle']/5 * 2
		self.defense = self.owner.attributes['Athleticism']/5 + self.owner.attributes['Grace']/5
	
	def take_damage(self, force, body_part, damage_type = 'blunt'):
		#print self.owner.name + "'s " + body_part.name + ' is taking damage'
		body_part.take_damage(force, damage_type)
		self.hp -= force/2
		if self.hp <= 0 or len(self.owner.body.parts) <= 0:
			if self.owner.ai is not None:
				self.owner.ai.death()

	def attack(self, target):
		#event!
		active_map.add_event(self.owner, verbs['attacks'], target)
	
		weapon = self.owner.weapon
		if weapon == None:
			weapon_name = 'fists'
			damage_type = 'blunt'
			damage_concentration = .5
			start_reverb = 25
			weapon_skill = 'martial arts'
		else:
			weapon_name = weapon.name
			damage_type = 'blunt'
			start_reverb = weapon.damage_reverb
			damage_concentration = weapon.damage_concentration
			weapon_skill = weapon.weapon_skill
			weapon = weapon.name
		#Punitive damages!
		(force, reverb) = vary_damage(int((self.owner.attributes['Muscle']/3)*damage_concentration), start_reverb)
		target_list = ()
		
		attack_roll = libtcod.random_get_int(0, self.power/4 * 3, self.power)
		if weapon_skill in self.owner.frontal_cortex.skills:
			attack_roll += self.owner.frontal_cortex.skills[weapon_skill]['level']
		#Aiming at them body parts! Random for now! Adjusted based on size!
		parts_list = []
		for part in target.body.parts:
			for i in range(part.size/10):
				parts_list.append(part.name)
		aimed = libtcod.random_get_int(0, 0, len(parts_list)-1)
		if aimed >= 0:
			try:
				for part in target.body.parts:
					if part.name == parts_list[aimed]:
						target_part = part
						if target_part.hp <= 0:
							target_part = target.body.parts[0]
				if reverb > target_part.size and target_part.parent != None and target_part.parent != 'CORE' and target_part.parent.hp > 0:
					force = force/2
					target_list = (target_part, target_part.parent)
			except IndexError:
				print 'Index Error!'
				for part in target.body.parts:
					print part.name
		else:
			attack_roll = target.fighter.defense-1
		
		if attack_roll > target.fighter.defense:
			if force > 0:
				if self.owner != player:
					message(self.owner.name + ' hits ' + target.name + ' in the ' + target_part.name + ' with their ' + weapon_name + ' for ' + str(force) + ' damage!', libtcod.red)
				else:
					message('You hit ' + target.name + ' in the ' + target_part.name + ' with your ' + weapon_name + ' for ' + str(force) + ' damage!', libtcod.white)
				#if target_list != ():
				#	for targ in target_list:
				#		if targ != target_part:
				#			if target.fighter != None:
				#				message("The hit reverberates through to the " + targ.name + " for " + str(force/2) + " damage!", libtcod.yellow)
				#				target.fighter.take_damage(force/2, targ)
				if target.fighter != None:
					target.fighter.take_damage(force, target_part, damage_type)
					target.change_opinion(self.owner, force*-2)
				self.owner.frontal_cortex.increase_skill(weapon_skill, libtcod.random_get_int(0, 1, 3))
			else:
				if self.owner != player:
					message("The " + self.owner.name + " hits " + target.name + " but the attack bounces off harmlessly.", libtcod.grey)
				else:
					message("You hit " + target.name + " but the attack bounces off harmlessly.", libtcod.grey)
		else:
			if self.owner != player:
				message("The " + self.owner.name + ' misses ' + target.name + ".", libtcod.grey)
			else:
				message('You miss ' + target.name + ".", libtcod.grey)

class AI:
	def __init__(self):
		self.type = 'none_ai'
		self.timer_max = libtcod.random_get_int(0, 20, 30)
		self.timer = self.timer_max
	
	def movement_decision(self):
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.timer = self.timer_max
	
	def death(self):
		#Poor AI, it was only a few days until retirement.
		message(self.owner.name + ' has died.', libtcod.dark_red)
		corpse = Item('corpse of ' + self.owner.name, self.owner.x, self.owner.y, libtcod.darker_red, '%')
		active_map.items.append(corpse)
		active_map.actors.remove(self.owner)
		self.owner.exit_tile()
		self.owner.fighter = None
		self.owner.blocks = False
		self.owner.ai = None

class Random_Move_AI(AI):
	def __init__(self):
		self.type = 'random_move_ai'
		self.timer_max = libtcod.random_get_int(0, 20, 30)
		self.timer = self.timer_max
	
	def movement_decision(self):
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.timer = self.timer_max

class Beeline_Attack_AI(AI):
	def __init__(self, target):
		self.type = 'beeline_attack_ai'
		self.timer_max = libtcod.random_get_int(0, 15, 25)
		self.timer = self.timer_max
		self.target = target
	
	def movement_decision(self):
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			self.owner.move_towards(self.target.x, self.target.y)
			self.timer = self.timer_max

class Flee_AI(AI):
	def __init__(self, target):
		self.type = 'flee_ai'
		self.timer_max = libtcod.random_get_int(0, 15, 25)
		self.timer = self.timer_max
		self.target = target
	
	def movement_decision(self):
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			self.owner.move_away(self.target.x, self.target.y)
			self.timer = self.timer_max

class Queue_AI(AI):
	def __init__(self):
		self.type = 'queue_ai'
		self.timer_max = libtcod.random_get_int(0, 20, 30)
		self.timer = self.timer_max
		self.target_x = None
		self.target_y = None
		self.prev_x = None
	
	def check_for_actors(self, x, y):
		for item in active_map.map[x][y].contents:
			if item.type == 'actor':
				if item != self.owner:
					return True
		return False
	
	def get_queue_target(self):
		self.target_x = active_map.queue_x
		self.target_y = active_map.queue_y
		while self.check_for_actors(self.target_x, self.target_y) or active_map.map[self.target_x][self.target_y].blocked:
			self.target_y += 1
	
	def shopkeeper_moved(self):
		if self.prev_x == None:
			self.prev_x = active_map.owner.shop.shopkeeper.x
			return False
		else:
			if self.prev_x != active_map.owner.shop.shopkeeper.x:
				self.prev_x = active_map.owner.shop.shopkeeper.x
				return True
			else:
				self.prev_x = active_map.owner.shop.shopkeeper.x
				return False
				
	def movement_decision(self):
		if self.target_x == None or self.check_for_actors(self.target_x, self.target_y) or self.shopkeeper_moved():
			self.get_queue_target()
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			if self.owner.y >= (active_map.height/4)*3:
				self.owner.move(0, -1)
				print 'moved up'
			else:
				self.owner.move_towards(self.target_x, self.target_y)
			self.timer = self.timer_max

class Shopkeep_AI(AI):
	def __init__(self, shop):
		self.shop = shop
		self.timer_max = libtcod.random_get_int(0, 100, 200)
		self.timer = self.timer_max
		
	def movement_decision(self):
		if self.timer > 0:
			self.timer -= 1
		elif self.timer == 0:
			self.owner.move(libtcod.random_get_int(0, -1, 1), 0)
			self.timer_max = libtcod.random_get_int(0, 100, 200)
			self.timer = self.timer_max

class Player_AI(AI):
	def __init__(self):
		self.type = 'player_ai'
		self.timer_max = 20
		self.timer = self.timer_max
		self.ready = False
	
	def movement_decision(self):
		global game_state
		if self.timer > 0:
			self.timer -= 1
	
	def death(self):
		global game_state
		#Player AI gets a special death function, because otherwise there are crashes.
		message('You have been killed. Please press ESC and return to the main menu.', libtcod.dark_red, True)
		corpse = Item('corpse of ' + self.owner.name, self.owner.x, self.owner.y, libtcod.darker_red, '%')
		active_map.items.append(corpse)
		active_map.actors.remove(self.owner)
		self.owner.exit_tile()
		self.owner.blocks = False
		#game_state = 'game_over'
		self.timer_max = 1

class Abstract_Actor:
	#Offscreen characters. These are the 'master classes' of any persistent actors in the game, excepting the player.
	def __init__(self, actor):
		self.actor = actor
		actor.abstract = self
		self.home = None
		self.generate_info()

	def generate_info(self):
		for place in places:
			if place.specials.count("livable") == 1:
				for floor in place.floors:
					if floor.inhabitant == None:
						self.home = floor
						floor.inhabitant = self
						break
	
	def spawn(self, x, y):
		print 'spawning', self.actor.name
		self.actor.x = x
		self.actor.y = y
		active_map.actors.append(self.actor)

#Meta-AI Classes (Emotional Brain)

#this cortex controls AIs on a macro scale.
class Frontal_Cortex:
	def __init__(self, owner):
		#This stores the mental and emotional aspects of an actor. I.E. Actor is the physical body, this is the frontal cortex (:O), the AI is the nervous system.
		self.owner = owner
		self.personality = {'Aggressiveness' : 50, 'Altruism' : 50, 'Fearlessness' : 50, 'Instability' : 50}
		self.skills = {}
		self.claimed_items = []
		self.attacking = []
		
		#this dictionary tracks all events that have been processed by the cortex.
		#the event is the key, its age is the value. once it has been in the dictionary
		#for a while it will be removed.
		#this will prevent event log spam.
		self.processed_events = {}
	
	def increase_skill(self, skill, xp):
		if skill in self.skills:
			self.skills[skill]['xp'] += xp
			if self.skills[skill]['xp'] > self.skills[skill]['level'] * 10:
				self.level_skill(skill)
		else:
			self.skills[skill] = {'xp' : xp, 'level' : 0}
			if xp > 5:
				self.level_skill(skill)
		#print self.owner.name + ' xp gain ' + skill + ' ' + str(xp)
	
	def level_skill(self, skill):
		self.skills[skill]['xp'] = 0
		self.skills[skill]['level'] += 1
		message(self.owner.name + ' has increased their ' + skill + ' skill to level ' + str(self.skills[skill]['level']) + '!')
	
	def claim_item(self, item):
		self.claimed_items.append(item)
	
	def combat_yield(self):
		message(self.owner.name + " has yielded to " + self.owner.ai.target.name + "!", libtcod.green)
		active_map.add_event(self.owner, verbs['yields'], self.owner.ai.target)

	def evaluate_threats(self):
		threatened = active_map.total_threat/(len(active_map.actors)-1) #average threat level of other actors in the area
		threatened -= self.owner.threat_level
		if self.owner.fighter.hp < self.owner.fighter.max_hp:
			threatened += self.owner.fighter.max_hp - self.owner.fighter.hp
		if threatened > self.personality['Fearlessness']:
			print self.owner.name + " is fleeing due to threat level " + str(threatened)
			return 'flee_ai'
	
	def scan_events(self):
		#Look through event log to see what happened.
		for event in active_map.events:
			if event not in self.processed_events:
				if event.verb.name == 'picks_up':
					#If someone picks up a claimed object
					if event.object in self.claimed_items:
						self.owner.change_opinion(event.subject, -5)
						message(event.subject.name + ' has picked up a ' + event.object.name + ' claimed by ' + self.owner.name + '!', libtcod.yellow)
				if event.verb.name == 'yields':
					#if somebody yields to somebody
					if event.object.name == self.owner.name:
						self.owner.plug_ai(Random_Move_AI())
						message(self.owner.name + " has accepted the yield.", libtcod.yellow)
			
			self.processed_events[event] = 1
		##### end of loop
		
		to_delete = []
		for event, age in self.processed_events.iteritems():
			self.processed_events[event] = age+1
			if self.processed_events[event] > 60:
				print "deleting item from AI cortex processed events"
				to_delete.append(event)
		for event in to_delete:
			del self.processed_events[event]
					
	def decision(self):
		if self.owner != player:
			#Look at event log, first.
			self.scan_events()
			#If you should be running, run!
			if self.evaluate_threats() == 'flee_ai' and self.owner.ai != 'flee_ai':
				self.owner.plug_ai(Flee_AI(player))
			#If in combat...
			elif self.owner.ai.type == 'beeline_attack_ai':
				#Evaluate HP and body integrity.
				no_severs = True
				for part in self.owner.body.parts:
					if part.flags['severed']:
						no_severs = False
				#Make a tactical retreat if wounded!
				if self.owner.fighter.hp < self.owner.fighter.hp/2 or no_severs == False:
					target = self.owner.ai.target
					self.owner.plug_ai(Flee_AI(target))
					self.combat_yield()
					message(self.owner.name + ' is running away!', libtcod.yellow)
		if self.owner.ai != None:
			self.owner.ai.movement_decision()

#this cortex figures out what the player is doing and performs cortex actions for them.
class Player_Cortex:
	def __init__(self, owner):
		#note that the owner will always be the player.
		self.owner = owner
		self.skills = {}
		self.claimed_items = []
		self.attacking = []
		
		#this dictionary tracks all events that have been processed by the cortex.
		#the event is the key, its age is the value. once it has been in the dictionary
		#for a while it will be removed.
		#this will prevent event log spam.
		self.processed_events = {}
	
	def scan_events(self):
		for event in active_map.events:
			if event not in self.processed_events:
				if event.verb.name == 'attacks':
					if event.subject == self.owner:
						already_attacking = False
						for actor in self.attacking:
							if actor == event.object:
								already_attacking = True
								break
						if not already_attacking:
							self.attacking.append(event.object)
				elif event.verb.name == 'yields':
					#if someone yields to the player, open a textbox
					if event.object.name == self.owner.name:
						message(event.subject.name + " has yielded to you!", libtcod.red, True)
				
				self.processed_events[event] = 1 #mark the event as processed
		####### end of loop
		
		to_delete = []
		for event, age in self.processed_events.iteritems():
			self.processed_events[event] = age+1
			if self.processed_events[event] > 60:
				print "deleting '" + str(event) + "' from player cortex processed events"
				to_delete.append(event)
		for event in to_delete:
			del self.processed_events[event]
		
	def combat_yield(self):
		message(self.owner.name + " has yielded to " + self.attacking[0].name + "!", libtcod.green)
		active_map.add_event(self.owner, verbs['yields'], self.attacking[0])
		
	def decision(self):
		self.scan_events()

#World Classes

class Bank:
	def __init__(self, owner, balance = 100):
		self.owner = owner
		owner.bank = self
		self.balance = 100

class Shop:
	def __init__(self, place):
		self.owner = place
		place.shop = self
		self.name = place.name
		self.inventory = {}
		self.shopkeeper = None
	
	def set_inventory(self, inv_dict):
		self.inventory = inv_dict
		for (item, price) in self.inventory.iteritems():
			self.shopkeeper.frontal_cortex.claim_item(item)
	
	def create_shopkeeper(self):
		#The actual shopkeeper must be created when the player enters.
		self.shopkeeper = create_offscreen_actor()
		self.shopkeeper.plug_ai(Shopkeep_AI(self))
		self.shopkeeper.x = self.owner.total_size/2
		self.shopkeeper.y = self.owner.building.y + self.owner.building_size/4 - 1
		
		self.owner.floors[0].actors.append(self.shopkeeper)

#Event Classes

class Event:
	def __init__(self, subject, verb, object):
		self.subject = subject
		self.verb = verb
		self.object = object
		self.age = 0
	
	def __str__(self):
		return self.verb.name

class Verb:
	def __init__(self, name, flags = None):
		self.name = name
		if flags == None:
			self.flags = {'possessive' : False, 'violent' : False, 'social' : False, 'visible' : False}
		else:
			self.flags = flags

#Social Classes

class Topic:
	#A topic of conversation- consists of the topic and its available phrases.
	def __init__(self, name):
		self.name = name
		self.phrases = []
		ender = Phrase('end')
		ender.text = "I have to go now."
		ender.phrase_id = "omni:ender"
		ender.ends_conv = True
		self.add_phrase(ender)
	
	def add_phrase(self, phrase):
		self.phrases.append(phrase)
	
	def print_topic(self):
		#print 'printing topic ' + self.name
		for phrase in self.phrases:
			print phrase.name + ' : ' + phrase.text

class Phrase:
	def __init__(self, name):
		self.name = name
		self.text = ""
		self.phrase_id = ""
		self.link_to_topic = ""
		self.abs_opinion_change = 0
		self.ends_conv = False

#Ability & Skill Classes

class Ability:
	def __init__(self, name, effect_type, damage):
		self.name = name
		self.effect_type = effect_type
		self.damage = damage
		self.effect = Visual_Effect(libtcod.dark_yellow, 2, 1, 100, {'type' : self.effect_type, 'velocity' : (1, 0)})
	
	def activate(self, x, y, velocity):
		self.effect.effect_info['velocity'] = velocity
		self.effect.activate_toggle(self, x, y, velocity)

#Item Classes

class Item:
	def __init__(self, name, x, y, color, char, weapon_stats = [], use = None):
		self.name = name
		self.x = x
		self.y = y
		self.color = color
		self.char = char
		self.type = 'item'
		self.blocks = False
		self.description = ['This is a ' + self.name + '.']
		self.weapon_skill = 'improvised weapons'
		if weapon_stats == []:
			self.damage_concentration = .5
			self.damage_reverb = 25
		else:
			self.damage_concentration = weapon_stats[0]
			self.damage_reverb = weapon_stats[1]
		if use == None:
			self.use = self.no_use
		else:
			self.use = use
	
	def copy(self, x=None, y=None):
		if x == None:
			x = self.x
		if y == None:
			y = self.y
		new_item = Item(self.name, x, y, self.color, self.char, [self.damage_concentration, self.damage_reverb], self.use)
		new_item.description = self.description
		new_item.weapon_skill = self.weapon_skill
		new_item.blocks = self.blocks
		return new_item
	
	def no_use(self):
		message("You can't use that!", libtcod.dark_yellow)

	def draw(self):
		if active_map.map[self.x][self.y].contents.count(self) == 0:
			active_map.map[self.x][self.y].contents.append(self)
		libtcod.console_set_foreground_color(active_map.con, self.color)
		libtcod.console_put_char(active_map.con, self.x, self.y, self.char, libtcod.BKGND_SET)
	
	def exit_tile(self):
		if active_map.map[self.x][self.y].contents.count(self) != 0:
			active_map.map[self.x][self.y].contents.remove(self)

class Phone(Item):
	def __init__(self, name, x, y, color, char, use = None):
		Item.__init__(self, name, x, y, color, char, [], use)
		self.contacts = []
	
	def add_contact(self, actor):
		self.contacts.append(actor)

#Body Classes

class Body:
	def __init__(self, name):
		self.name = name
		self.owner = None
		self.hubs = []
		self.limbs = []
		self.parts = []
		self.segments = []
	
	def setup(self):
		#Get the list of important parts, to clean up list displays.
		self.important_parts = []
		#Get the body's total max HP. This is important for the Fighter module!
		self.total_hp = 0
		for part in self.parts:
			part.max_hp = part.size
			part.hp = part.max_hp
			part.wound_hp = part.max_hp
			if part.flags['important'] == True:
				self.important_parts.append(part)
			self.total_hp += part.hp
	
	def spawn_new(self):
		#This function is only used when creating a body to assign to an actor. It returns a new Body object identical to itself.
		#Since every Hub & Limb object has to be connected to another one, the function can basically just run down the tree until there aren't any branches left.
		#This allows it to avoid keeping a dictionary of yet-to-be-copied things.
		#print "spawning a new body"
		new_body = Body(self.name)
		for part in self.parts:
			if part.name == 'torso':
				new_core = Hub(part.name)
				new_core.size = part.size
				new_core.flags = part.flags
				new_body.add_hub(new_core, 'CORE')
			elif part.type == 'hub':
				new_hub = Hub(part.name)
				#print 'new hub with name', new_hub.name
				new_hub.size = part.size
				new_hub.flags = part.flags
				for bit in new_body.parts:
					if part.parent.name == bit.name:
						new_body.add_hub(new_hub, bit)
			elif part.type == 'limb':
				new_limb = Limb(part.name)
				#print 'new limb with name', new_limb.name
				new_limb.size = part.size
				new_limb.flags = part.flags
				for bit in new_body.parts:
					if part.parent.name == bit.name:
						new_body.add_limb(new_limb, bit)
		#print "body spawned with name", new_body.name
		new_body.setup()
		return new_body

	def add_hub(self, hub, connection):
		if self.hubs == []:
			connection = 'CORE'
		else:
			connection.children.append(hub)
		for part in self.parts:
			if part.name == connection:
				hub.parent = connection
		self.parts.append(hub)
		self.hubs.append(hub)
		hub.owner = self
	
	def add_limb(self, limb, hub):
		self.parts.append(limb)
		self.limbs.append(limb)
		hub.children.append(limb)
		limb.parent = hub
		limb.owner = self

class Segment:
	def __init__(self, name):
		self.name = name
		self.parts = []
	
	def add_limb(self, limb, parent_limb = None):
		if parent_limb == None:
			self.parts.append(limb)
			limb.parent = self

class Hub:
	def __init__(self, name):
		self.name = name
		self.parent = None
		self.children = []
		self.item = None
		self.type = 'hub'
		self.flags = {}
		for (k, v) in body_part_flags.iteritems():
			self.flags[k] = v
		self.max_hp = 10
		self.hp = self.max_hp
	
	def get_status(self):
		if self.hp == self.max_hp:
			return ('pristine', libtcod.white)
		elif self.hp >= 3*self.max_hp/4:
			return ('scraped', libtcod.light_grey)
		elif self.hp >= self.max_hp/2:
			return ('wounded', libtcod.light_red)
		elif self.hp >= self.max_hp/4:
			return ('crippled', libtcod.red)
		elif self.hp == 1:
			return ('all but destroyed', libtcod.dark_red)
		elif self.hp <= 0:
			return ('severed!', libtcod.darker_red)
		return ('severed!', libtcod.darker_red)
	
	def take_damage(self, damage, damage_type):
		if damage_type == 'blunt':
			self.hp -= damage
		elif damage_type == 'cut':
			self.hp -= damage
			self.wound_hp -= damage
		if self.wound_hp <= 0:
			self.die()
	
	def die(self):
		if self.hp > 0:
			self.hp = 0
		self.parent = None
		for child in self.children:
			child.die()
		self.children = []
		if self.owner.owner != None:
			active_map.map[self.owner.owner.x][self.owner.owner.y].color = libtcod.dark_red
			active_map.items.append(Item('severed ' + self.name, self.owner.owner.x, self.owner.owner.y, libtcod.darker_red, 'l'))
		self.owner.parts.remove(self)
		message(self.name + " falls to the ground, lifeless!", libtcod.dark_red)
		print self.name, 'is severed'
	
	def cripple(self):
		message(self.name + " is crippled")

class Limb:
	def __init__(self, name, size=5):
		self.name = name
		self.parent = None
		self.children = []
		self.item = None
		self.flags = {}
		for (k, v) in body_part_flags.iteritems():
			self.flags[k] = v
		self.type = 'limb'
		self.max_hp = 10
		self.hp = self.max_hp
		self.wound_hp = self.max_hp
	
	def get_status(self):
		if self.hp == self.max_hp:
			return ('pristine', libtcod.white)
		elif self.hp >= 3*self.max_hp/4:
			return ('scraped', libtcod.light_grey)
		elif self.hp >= self.max_hp/2:
			return ('wounded', libtcod.light_red)
		elif self.hp >= self.max_hp/4:
			return ('crippled', libtcod.red)
		elif self.hp == 1:
			return ('all but destroyed', libtcod.dark_red)
		elif self.hp <= 0:
			return ('severed!', libtcod.darker_red)
		return ('severed!', libtcod.darker_red)
	
	def take_damage(self, damage, damage_type):
		self.hp -= damage
		#elif damage_type == 'cut':
		#	self.hp -= damage
		#	self.wound_hp -= damage
		if self.hp <= 0:
			self.die()
	
	def die(self):
		if self.hp > 0:
			self.hp = 0
		self.parent = None
		for child in self.children:
			child.die()
		self.children = []
		if self.owner.owner != None:
			active_map.map[self.owner.owner.x][self.owner.owner.y].color = libtcod.dark_red
			active_map.items.append(Item('severed ' + self.name, self.owner.owner.x, self.owner.owner.y, libtcod.darker_red, 'l'))
		message(self.name + " is severed!", libtcod.dark_red)
		print self.name, 'is severed from', self.owner.owner.name
		self.flags['severed'] = True
		
		if self.flags['vital'] == True and self.owner.owner.ai != None:
			print self.owner.owner.name, 'decapped'
			self.owner.owner.ai.death()
	
	def cripple(self):
		message(self.name + ' is crippled')
		if self.parent is not None:
			self.parent.take_damage(2)

#Parsing Classes
	
class EmptyListener:
	def new_struct(self, struct, name):
		print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		return True
	def new_flag(self, name):
		print 'new flag named ', name
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE']
		if typ == libtcod.TYPE_COLOR:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		elif typ == libtcod.TYPE_DICE:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		else:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value
		return True
	def end_struct(self, struct, name):
		print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

class BodyListener:
	def new_struct(self, struct, name):
		print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		if libtcod.struct_get_name(struct) == "body_type":
			BODIES.append(Body(name))
			self.active_body = BODIES[len(BODIES)-1]
			self.active = None
			self.parts = []
		elif libtcod.struct_get_name(struct) == "new_hub":
			self.active = Hub(name)
			self.parent = None
			self.parts.append(self.active)
		elif libtcod.struct_get_name(struct) == "new_limb":
			self.active = Limb(name)
			self.parent = None
			self.parts.append(self.active)
		self.parent = 'CORE'
		return True
	def new_flag(self, name):
		print 'new flag named ', name
		self.active.flags[name.lower()] = True
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE']
		if typ == libtcod.TYPE_COLOR:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		elif typ == libtcod.TYPE_DICE:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		else:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value
		if name == "parent":
			for part in self.parts:
				if part.name == value:
					self.parent = part
					print self.active.name, 'parent', self.parent.name
			if self.parent == None:
				print self.active.name, 'no parent'
		elif name == "size":
			self.active.size = value
			self.active.max_hp = value
			self.active.hp = value
		return True
	def end_struct(self, struct, name):
		print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		if self.active:
			if self.active.type == 'hub':
				self.active_body.add_hub(self.active, self.parent)
			elif self.active.type == 'limb':
				self.active_body.add_limb(self.active, self.parent)
			self.active = None
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

class PlaceListener:
	def new_struct(self, struct, name):
		print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		self.active_map_name = name
		self.active_floors = 1
		self.active_specials = []
		return True
	def new_flag(self, name):
		print 'new flag named ', name
		self.active_specials.append(name.lower())
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE', 'VALUELIST']
		if typ == libtcod.TYPE_COLOR:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		elif typ == libtcod.TYPE_DICE:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		else:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value
			if name == 'name':
				self.active_name = value
			elif name == 'total_size':
				self.active_total_size = value
			elif name == 'building_size':
				self.active_building_size = value
			elif name == 'floors':
				self.active_floors = value
			elif name == 'spawn_rate':
				self.active_spawn_rate = value
			elif name == 'name_gen_list':
				self.active_name_gen_list = value
		return True
	def end_struct(self, struct, name):
		global gen_name
		print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		new_place = Place(self.active_name, self.active_total_size, self.active_building_size, self.active_floors, self.active_spawn_rate, self.active_specials)
		new_place.name_gen_list = self.active_name_gen_list
		places.append(new_place)
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

class ItemListener:
	def new_struct(self, struct, name):
		print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		self.active_id = name
		self.active_weapon_skill = 'improvised weapons'
		return True
	def new_flag(self, name):
		print 'new flag named ', name
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE']
		if typ == libtcod.TYPE_COLOR:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		elif typ == libtcod.TYPE_DICE:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		else:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value
		if name == 'char':
			self.active_char = value[0]
		elif name == 'name':
			self.active_name = value
		elif name == 'description':
			self.active_description = value
		elif name == 'damage_concentration':
			self.active_damage_concentration = value
		elif name == 'damage_reverb':
			self.active_damage_reverb = value
		elif name == 'weapon_skill':
			self.active_weapon_skill = value
		return True
	def end_struct(self, struct, name):
		print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		self.active_item = Item(self.active_name, 0, 0, random_color(), self.active_char, [self.active_damage_concentration, self.active_damage_reverb])
		self.active_item.description = self.active_description
		self.active_item.weapon_skill = self.active_weapon_skill
		all_items[self.active_id] = self.active_item
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

class ConvListener:
	def new_struct(self, struct, name):
		#print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		if libtcod.struct_get_name(struct) == "topic_struct":
			self.active_topic = Topic(name)
		if libtcod.struct_get_name(struct) == "phrase_struct":
			self.active = Phrase(name)
		return True
	def new_flag(self, name):
		#print 'new flag named ', name
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE']
		#if typ == libtcod.TYPE_COLOR:
			#print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		#elif typ == libtcod.TYPE_DICE:
			#print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		#else:
			#print 'new property named ', name, ' type ', type_names[typ], ' value ', value
		if name == 'phrase_text':
			self.active.text = value
		elif name == 'phrase_id':
			self.active.phrase_id = value
		elif name == 'link_to_topic':
			self.active.link_to_topic = value
		elif name == 'abs_opinion_change':
			self.active.abs_opinion_change = value
		return True
	def end_struct(self, struct, name):
		#print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		if libtcod.struct_get_name(struct) == 'phrase_struct':
			self.active_topic.add_phrase(self.active)
			self.active = None
		elif libtcod.struct_get_name(struct) == 'topic_struct':
			self.active_topic.phrases.reverse()
			conv_topics[self.active_topic.name] = self.active_topic
			self.active_topic = None
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

class VerbListener:
	def new_struct(self, struct, name):
		print 'new structure type', libtcod.struct_get_name(struct), ' named ', name
		self.active_verb = Verb(name)
		return True
	def new_flag(self, name):
		print 'new flag named ', name
		self.active_verb.flags[name] = True
		return True
	def new_property(self, name, typ, value):
		type_names = ['NONE', 'BOOL', 'CHAR', 'INT', 'FLOAT', 'STRING', 'COLOR', 'DICE']
		if typ == libtcod.TYPE_COLOR:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.r, value.g, value.b
		elif typ == libtcod.TYPE_DICE:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value.nb_dices, value.nb_faces, value.multiplier, value.addsub
		else:
			print 'new property named ', name, ' type ', type_names[typ], ' value ', value
		return True
	def end_struct(self, struct, name):
		print 'end structure type', libtcod.struct_get_name(struct), ' named ', name
		verbs[self.active_verb.name] = self.active_verb
		self.active_verb = None
		return True
	def error(self, msg):
		print 'error: ', msg
		return True

##########
#FUNCTIONS
##########

#Rendering Functions

def render_menu(menu, option, color, OP_X, OP_Y):
	#Quick n' easy menu rendering.
	libtcod.console_set_foreground_color(panel1, color)
	for item in menu:
		if item == menu[option]:
			libtcod.console_print_left(panel1, OP_X, OP_Y, libtcod.BKGND_NONE, item + '  *')
		else:
			libtcod.console_print_left(panel1, OP_X, OP_Y, libtcod.BKGND_NONE, item)
		OP_Y += 2

def renderable_area(x1, y1, width, height, console):
	#Trim the specified render area to something that won't crash.
	con_width = libtcod.console_get_width(console)
	con_height = libtcod.console_get_height(console)
	
	while x1 < 0:
		x1 += 1
	while y1 < 0:
		y1 += 1
	while x1+width > con_width-1:
		if libtcod.console_get_width(panel1) > con_width:
			width -= 1
		else:
			x1 -= 1
	while y1+height > con_height-1:
		if libtcod.console_get_height(panel1) > con_height:
			height -= 1
		else:
			y1 -= 1
	
	return (x1, y1, width, height)

def render_panel_border(panel, color):
	#Takes a console and renders a wall of '#'s around its edge in the specified color.
	draw_x = 0
	draw_y = 0
	panel_width = libtcod.console_get_width(panel)-1
	panel_height = libtcod.console_get_height(panel)-1
	
	libtcod.console_set_foreground_color(panel, color)
	
	for x in range(panel_width):
		libtcod.console_put_char(panel, draw_x, 0, '#')
		libtcod.console_put_char(panel, draw_x, panel_height, '#')
		draw_x += 1
	
	for y in range(panel_height):
		libtcod.console_put_char(panel, 0, draw_y, '#')
		libtcod.console_put_char(panel, panel_width, draw_y, '#')
		draw_y += 1
	
	libtcod.console_put_char(panel, draw_x, draw_y, '#')

def outline_rect(panel, color, draw_x, draw_y, width, height):
	#Like render_panel_border, only more generalized.
	base_x = draw_x
	base_y = draw_y
	libtcod.console_set_foreground_color(panel, color)
	
	#Draw the top & bottom walls.
	for x in range(width):
		libtcod.console_put_char(panel, draw_x, base_y, '#')
		libtcod.console_put_char(panel, draw_x, base_y+height, '#')
		draw_x += 1
	#Draw the left & right walls.
	for y in range(height):
		libtcod.console_put_char(panel, base_x, draw_y, '#')
		libtcod.console_put_char(panel, base_x+width, draw_y, '#')
		draw_y += 1
	libtcod.console_put_char(panel, draw_x, draw_y, '#')

def message(new_msg, color = libtcod.white, box = False):
	global game_msgs, game_msgs_backlog, game_state, textbox_lines
	if box == True:
		#empty the buffer
		textbox_lines = []
		#Split, if necessary
		new_msg_lines = textwrap.wrap(new_msg, libtcod.console_get_width(panel2)-3)
		#Now sort out the lines.
		game_msgs_backlog.append( ("#", libtcod.grey) )
		for line in new_msg_lines:
			textbox_lines.append((line, color))
			game_msgs_backlog.append( ("# " + line, libtcod.grey) ) #TEMPORARY
		game_msgs_backlog.append( ("#", libtcod.grey) )
		
		#ensure that the backlog isn't too big
		while len(game_msgs_backlog) >= libtcod.console_get_height(window_panel)-10:
			del game_msgs_backlog[0]
		
		game_state = 'textbox'
	else:
		#Split, if necessary
		new_msg_lines = textwrap.wrap(new_msg, libtcod.console_get_width(panel2)-2)
		new_msg_lines.append("SKIPLINE")
		for line in new_msg_lines:
			#If the default buffer is full, remove the first line.
			if len(game_msgs) >= libtcod.console_get_height(panel2)-6:
				del game_msgs[0]
			#If the detailed buffer is full, remove the first line.
			if len(game_msgs_backlog) >= libtcod.console_get_height(window_panel)-10:
				del game_msgs_backlog[0]
				
			#Add new line as a tuple.
			if line == "SKIPLINE":
				line = " "
			game_msgs.append( (line, color) )
			game_msgs_backlog.append( (line, color) )

def render_all():
	global active_map, panels, title_menu, menu_option, look_focus, conv_topic, conv_topics, current_list, textbox_lines
	#Draw panels, blit them to con, blit con to root, flush.
	
	#Render panel borders with a very aptly-named function.
	render_panel_border(panel1, libtcod.dark_violet)
	render_panel_border(panel2, libtcod.dark_blue)
	render_panel_border(panel3, libtcod.dark_green)
	render_panel_border(panel4, libtcod.dark_cyan)
	
	#Main game states- play, look, etc.
	if game_state.find('_menu') == -1:
		#Draw items.
		for item in active_map.items:
			item.draw()
		#Draw actors on top of items.
		for actor in active_map.actors:
			actor.draw()
		#Draw map tiles.
		for x in range(libtcod.console_get_width(active_map.con)):
			for y in range(libtcod.console_get_height(active_map.con)):
				#Colors!
				libtcod.console_set_back(active_map.con, x, y, active_map.map[x][y].color, libtcod.BKGND_SET)
		#Draw effects on top of everything.
		for effect in active_map.effects:
			for particle in effect.particles:
				particle.draw()
	
		#Blit map console to panel1.
		#First, collect the renderable area (x, y, width, height).
		if active_map.width > libtcod.console_get_width(panel1)-2 or active_map.height > libtcod.console_get_width(panel1)-2:
			map_draw_x = player.x-20
			map_draw_y = player.y-15
			map_draw_w = 58
			map_draw_h = 40
			(map_draw_x, map_draw_y, map_draw_w, map_draw_h) = renderable_area(map_draw_x, map_draw_y, 58, 40, active_map.con)
			blit_x = 1
			blit_y = 1
		else:
			map_draw_x = 0
			map_draw_y = 0
			map_draw_w = active_map.width
			map_draw_h = active_map.height
			blit_x = (libtcod.console_get_width(panel1)/2)-(active_map.width/2)
			blit_y = (libtcod.console_get_height(panel1)/2)-(active_map.height/2)-1

		#Then, blit.
		libtcod.console_blit(active_map.con, map_draw_x, map_draw_y, map_draw_w, map_draw_h, panel1, blit_x, blit_y)
	
		#Display the game messages.
		MSG_Y = 5
		for (line, color) in game_msgs:
			libtcod.console_set_foreground_color(panel2, color)
			libtcod.console_print_left(panel2, 2, MSG_Y, libtcod.BKGND_NONE, line)
			MSG_Y += 1
	
		#Display also a little --- buffer between the messages and the look text.
		libtcod.console_set_foreground_color(panel2, libtcod.white)
		blex = 1
		for x in range(libtcod.console_get_width(panel2)/2):
			libtcod.console_put_char(panel2, blex, 3, '-')
			blex += 1
		
		#Conversation window! It has to blit to con, so blitting doesn't come until later.
		if game_state == 'conv_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, player.conversation_partner.name + ' says:')
			libtcod.console_print_left(window_panel, 3, 8, libtcod.BKGND_NONE, '"' + player.conversation_partner.conversation_string + '"')
			libtcod.console_print_left(window_panel, 3, libtcod.console_get_height(window_panel)-5, libtcod.BKGND_NONE, "Press ENTER to return to the game.")
			print_y = 12
			for phrase in conv_topics[conv_topic].phrases:
				if phrase == conv_topics[conv_topic].phrases[menu_option]:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, phrase.text + '  *')
				else:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, phrase.text)
				print_y += 2
		#Player info window! Blitting still comes later.
		elif game_state == 'info_window':
			#Print general info
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Player Info')
			libtcod.console_print_left(window_panel, 3, 8, libtcod.BKGND_NONE, 'Name: ' + player.name)
			if player.location != 'travel':
				libtcod.console_print_left(window_panel, 3, 10, libtcod.BKGND_NONE, 'Location: ' + player.location.name)
			else:
				libtcod.console_print_left(window_panel, 3, 10, libtcod.BKGND_NONE, 'Location: traveling')
			print_x = libtcod.console_get_width(window_panel)/2 + 3
			print_y = 16
			
			#Print the player's physical condition
			libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, 'Health Status')
			print_y += 3
			for part in player.body.important_parts:
				if part != None:
					libtcod.console_set_foreground_color(window_panel, part.get_status()[1])
					libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, part.name.capitalize() + ': ' + part.get_status()[0])
				else:
					libtcod.console_set_foreground_color(window_panel, libtcod.darker_red)
					libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, 'BLEEDING STUMP!')
				print_y += 2
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_left(window_panel, 3, libtcod.console_get_height(window_panel)-5, libtcod.BKGND_NONE, "Press SPACEBAR to return to the game.")
		#Inventory window! Etc. etc.
		elif game_state == 'inv_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Player Inventory')
			print_y = 8
			for part in player.body.important_parts:
				libtcod.console_set_foreground_color(window_panel, libtcod.white)
				libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, part.name.capitalize())
				if part.item != None:
					libtcod.console_set_foreground_color(window_panel, libtcod.light_grey)
					libtcod.console_print_left(window_panel, 5, print_y+1, libtcod.BKGND_NONE, part.item.name)
				else:
					libtcod.console_set_foreground_color(window_panel, libtcod.grey)
					libtcod.console_print_left(window_panel, 5, print_y+1, libtcod.BKGND_NONE, "Nothing")
				print_y += 3
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_left(window_panel, libtcod.console_get_width(window_panel)/2+3, 8, libtcod.BKGND_NONE, "\"Bag of Holding\"")
			libtcod.console_set_foreground_color(window_panel, libtcod.light_grey)
			print_y = 11
			for item in player.abstract_inv:
				if item == player.abstract_inv[menu_option]:
					libtcod.console_print_left(window_panel, libtcod.console_get_width(window_panel)/2+5, print_y, libtcod.BKGND_NONE, item.name + '   *')
				else:
					libtcod.console_print_left(window_panel, libtcod.console_get_width(window_panel)/2+5, print_y, libtcod.BKGND_NONE, item.name)
				print_y += 2
		#The window for dropping.
		elif game_state == 'drop_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			width = libtcod.console_get_width(window_panel)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Drop Which Item?')
			print_y = 8
			for part in player.body.important_parts:
				libtcod.console_set_foreground_color(window_panel, libtcod.white)
				if current_list == player.body.important_parts and part == player.body.important_parts[menu_option]:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, part.name.capitalize() + '  *')
				else:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, part.name.capitalize())
				libtcod.console_set_foreground_color(window_panel, libtcod.light_grey)
				if part.item != None:
					libtcod.console_print_left(window_panel, 5, print_y+1, libtcod.BKGND_NONE, part.item.name)
				else:
					libtcod.console_print_left(window_panel, 5, print_y+1, libtcod.BKGND_NONE, "Nothing")
				print_y += 3
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_left(window_panel, width/2+3, 8, libtcod.BKGND_NONE, "\"Bag of Holding\"")
			print_y = 11
			libtcod.console_set_foreground_color(window_panel, libtcod.light_grey)
			for item in player.abstract_inv:
				if current_list == player.abstract_inv and item == player.abstract_inv[menu_option]:
					libtcod.console_print_left(window_panel, width/2+5, print_y, libtcod.BKGND_NONE, item.name + '  *')
				else:
					libtcod.console_print_left(window_panel, width/2+5, print_y, libtcod.BKGND_NONE, item.name)
				print_y += 2
		#The window for viewing message backlog.
		elif game_state == 'message_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Messages')
			print_y = 8
			for (line, color) in game_msgs_backlog:
				libtcod.console_set_foreground_color(window_panel, color)
				libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, line)
				print_y += 1
		#Upon closer examination...
		elif game_state == 'look_window':
			look_tile = active_map.map[cursor.x][cursor.y]
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Examine what?')
			print_y = 8
			for k in look_tile.contents:
				if k.type != 'cursor' and k.type != 'map':
					if k == look_tile.contents[menu_option]:
						libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, k.name.capitalize() + '  *')
					else:
						libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, k.name.capitalize())
					print_y += 2
		#Upon EVEN CLOSER examination...
		elif game_state == 'look_focus_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Examining ' + look_focus.name)
			print_y = 8
			for k in look_focus.description:
				libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, k)
				print_y += 2
			
			if isinstance(look_focus, Actor):
				#Print an actor's physical condition
				print_x = libtcod.console_get_width(window_panel)/2 + 3
				libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, 'Health Status')
				print_y += 3
				for part in look_focus.body.important_parts:
					if part != None:
						libtcod.console_set_foreground_color(window_panel, part.get_status()[1])
						libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, part.name.capitalize() + ': ' + part.get_status()[0])
					else:
						libtcod.console_set_foreground_color(window_panel, libtcod.darker_red)
						libtcod.console_print_left(window_panel, print_x, print_y, libtcod.BKGND_NONE, 'BLEEDING STUMP!')
					print_y += 2
		#Ability menu!
		elif game_state == 'ability_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Abilities')
			print_y = 8
			for k in player.abilities:
				libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, str(player.abilities.index(k)+1) + ') ' + k.name)
				print_y += 2
		#Phone menu!
		elif game_state == 'phone_window':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			libtcod.console_print_center(window_panel, libtcod.console_get_width(window_panel)/2, 5, libtcod.BKGND_NONE, 'Contacts')
			print_y = 8
			for k in player_phone.contacts:
				if k == player_phone.contacts[menu_option]:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, k.name + '  *')
				else:
					libtcod.console_print_left(window_panel, 3, print_y, libtcod.BKGND_NONE, k.name)
				print_y += 2
		#Textboxes!
		elif game_state == 'textbox':
			libtcod.console_set_foreground_color(window_panel, libtcod.white)
			print_y = 2
			for (line, color) in textbox_lines:
				if line == "SKIPLINE":
					line = ''
				libtcod.console_set_foreground_color(window_panel, color)
				libtcod.console_print_left(window_panel, 2, print_y, libtcod.BKGND_NONE, line)
				print_y += 1
		
		#Now, panel3- the General Game Status pane.
		
		#Now, panel4- the Player Info At A Glance pane.
		libtcod.console_set_foreground_color(panel4, libtcod.white)
		libtcod.console_print_center(panel4, libtcod.console_get_width(panel4)/2, 2, libtcod.BKGND_NONE, "Player Info")
		libtcod.console_print_left(panel4, 2, 5, libtcod.BKGND_NONE, "Name: " + player.name)
		libtcod.console_print_left(panel4, 2, 7, libtcod.BKGND_NONE, "Health: " + str(player.fighter.hp) + '/' + str(player.fighter.max_hp))
		libtcod.console_print_left(panel4, 2, 9, libtcod.BKGND_NONE, "Cash: $" + str(player.bank.balance))
		
	#Title menu.
	elif game_state == 'title_menu':
		#Print the title and subtitle.
		libtcod.console_set_foreground_color(panel1, libtcod.red)
		libtcod.console_print_center(panel1, libtcod.console_get_width(panel1)/2, 6, libtcod.BKGND_NONE, "DASTARDLY")
		libtcod.console_set_foreground_color(panel1, libtcod.dark_red)
		libtcod.console_print_center(panel1, libtcod.console_get_width(panel1)/2, 9, libtcod.BKGND_NONE, "A game of style, subterfuge, and superweapons")
		
		#Print the options on the menu.
		render_menu(title_menu, menu_option, libtcod.light_grey, 9, 24)
	
	#Escape menu.
	elif game_state == 'esc_menu':
		libtcod.console_set_foreground_color(panel1, libtcod.red)
		libtcod.console_print_center(panel1, libtcod.console_get_width(panel1)/2, 6, libtcod.BKGND_NONE, "PAUSED")
		
		#Print the options.
		render_menu(esc_menu, menu_option, libtcod.light_grey, 9, 24)
	
	elif game_state == 'game_setup_menu':
		libtcod.console_set_foreground_color(panel1, libtcod.green)
		libtcod.console_print_center(panel1, libtcod.console_get_width(panel1)/2, 6, libtcod.BKGND_NONE, "Setup New User")
		
		#Print the options.
		if game_setup_menu[slide] != 'TEXT':
			render_menu(game_setup_menu[slide], menu_option, libtcod.light_grey, 9, 24)
	
	#Blit panels to con, in preparation for blitting con to root.
	libtcod.console_blit(panel1, 0, 0, 2*THIRD_W, 3*QUARTER_H, con, THIRD_W, 2)
	libtcod.console_blit(panel2, 0, 0, 2*THIRD_W, QUARTER_H+2, con, THIRD_W, 3*QUARTER_H + 2)
	libtcod.console_blit(panel3, 0, 0, THIRD_W, HALF_H, con, 0, 2)
	libtcod.console_blit(panel4, 0, 0, THIRD_W, HALF_H, con, 0, HALF_H + 2)
	
	#If a window is being used, blit that to con.
	if game_state.find('_window') != -1:
		render_panel_border(window_panel, libtcod.grey)
		libtcod.console_blit(window_panel, 0, 0, 3*QUARTER_W, 3*QUARTER_H, con, int(.5*QUARTER_W), int(.5*QUARTER_H))
	#Or perhaps you wanted a message box?
	elif game_state == 'textbox':
		outline_rect(window_panel, libtcod.grey, 0, 0, libtcod.console_get_width(panel2), len(textbox_lines)+3)
		center_x = HALF_W - libtcod.console_get_width(panel2)/2
		center_y = HALF_H - (len(textbox_lines)+4)/2
		libtcod.console_blit(window_panel, 0, 0, libtcod.console_get_width(panel2)+1, len(textbox_lines)+4, con, int(.5*QUARTER_W), center_y)
	
	#Display something on con at the top.
	libtcod.console_print_center(con, HALF_W, 0, libtcod.BKGND_NONE, 'DASTARDLY')
	
	#Blit con to the root.
	libtcod.console_blit(con, 0, 0, SCREEN_W, SCREEN_H, 0, 0, 0)
	
	libtcod.console_flush()

#Control Functions

def handle_keys():
	global game_state, active_map, menu_option, title_menu, slide, previous_state, look_focus, conv_topics, conv_topic, current_list, all_items, player_cortex
	
	key_buffer = False
	
	if game_state != 'play':
		key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
	elif game_state == 'play' and player.ai.timer == 0:
		key = libtcod.console_wait_for_keypress(True)
	else:
		key = libtcod.Key
	
	move_x = None
	move_y = None
	
	#Title Menu Controls
	if game_state == 'title_menu':
		menu_option = menu_control(title_menu, menu_option, key)
		if key.vk == libtcod.KEY_ENTER:
			print menu_option, title_menu[menu_option]
			if title_menu[menu_option] == 'New Game':
				menu_option = 0
				slide = 0
				player_setup()
				game_state = 'game_setup_menu'
			elif title_menu[menu_option] == 'Load Game':
				libtcod.console_print_left(panel1, 30, 26, libtcod.BKGND_NONE, "NO!")
			elif title_menu[menu_option] == 'Exit (ESC)' or key.vk == libtcod.KEY_ESCAPE:
				return 'exit'
	
	#Escape Menu Controls
	elif game_state == 'esc_menu':
		menu_option = menu_control(esc_menu, menu_option, key)
		if key.vk == libtcod.KEY_ENTER:
			if esc_menu[menu_option] == 'Back to Game':
				game_state = previous_state
			elif esc_menu[menu_option] == 'Quit to Title':
				menu_option = 0
				game_state = 'title_menu'
			elif esc_menu[menu_option] == 'Quit Game' or key.vk == libtcod.KEY_ESCAPE:
				return 'exit'
	
	#Game Setup Menu Controls
	elif game_state == 'game_setup_menu':
		if game_setup_menu[slide] != 'TEXT':
			menu_option = menu_control(game_setup_menu[slide], menu_option, key)
			if key.vk == libtcod.KEY_ENTER:
				print game_setup_menu[slide][menu_option]
				if slide == 0:
					player.gender = game_setup_menu[slide][menu_option]
				if slide + 1 < len(game_setup_menu):
					slide += 1
				else:
					game_state = 'play'
		else:
			proposed = ''
			while proposed == '':
				proposed = text_input(panel1, 9, 24)
			player.name = proposed
			player.setup_description()
			game_state = 'play'
	
	if key.vk == libtcod.KEY_ESCAPE and game_state != 'title_menu':
		menu_option = 0
		if game_state != 'esc_menu':
			previous_state = game_state
			game_state = 'esc_menu'
		else:
			return 'exit'

	elif key.vk == libtcod.KEY_ESCAPE and game_state == 'title_menu':
		return 'exit'
	
	#Drop Menu Controls
	elif game_state == 'drop_window':
		if current_list == player.body.important_parts:
			menu_option = menu_control(player.body.important_parts, menu_option, key)
			if key.vk == libtcod.KEY_ENTER:
				if player.body.important_parts[menu_option].item != None:
					message('You drop the ' + player.body.important_parts[menu_option].item.name + '.')
					player.drop(player.body.important_parts[menu_option].item)
					game_state = 'play'
				else:
					message('There is no item there.')
					game_state = 'play'
		elif current_list == player.abstract_inv:
			menu_option = menu_control(player.abstract_inv, menu_option, key)
			if key.vk == libtcod.KEY_ENTER:
				if player.abstract_inv[menu_option] != None:
					message('You drop the ' + player.abstract_inv[menu_option].name + '.')
					player.drop(player.abstract_inv[menu_option])
					game_state = 'play'
				else:
					message('There is no item there.')
					game_state = 'play'
		if key.vk == libtcod.KEY_LEFT:
			if menu_option > len(player.body.important_parts)-1:
				menu_option = len(player.body.important_parts)-1
			current_list = player.body.important_parts
		elif key.vk == libtcod.KEY_RIGHT:
			if menu_option > len(player.abstract_inv)-1:
				menu_option = len(player.abstract_inv)-1
			current_list = player.abstract_inv
	#Inventory Menu Controls
	elif game_state == 'inv_window':
		menu_option = menu_control(player.abstract_inv, menu_option, key)
		if key.vk == libtcod.KEY_ENTER and len(player.abstract_inv) > 0:
			player.abstract_inv[menu_option].use()
	#Examine Menu Controls
	elif game_state == 'look_window':
		available = active_map.map[cursor.x][cursor.y].contents
		for k in available:
			if k.type == 'cursor' or k.type == 'map':
				available.remove(k)
		menu_option = menu_control(available, menu_option, key)
		if key.vk == libtcod.KEY_ENTER:
			while True:
				try:
					look_focus = active_map.map[cursor.x][cursor.y].contents[menu_option]
					if look_focus.type != 'cursor' and look_focus.type != 'map':
						key_buffer = True
						game_state = 'look_focus_window'
					break
				except AttributeError:
					message(active_map.map[cursor.x][cursor.y].contents[menu_option].name)
					game_state = 'play'
					break
	#Conversation Menu Controls
	elif game_state == 'conv_window':
		menu_option = menu_control(conv_topics[conv_topic].phrases, menu_option, key)
		selected_phrase = conv_topics[conv_topic].phrases[menu_option]
		if key.vk == libtcod.KEY_ENTER:
			player.conversation_partner.process_phrase(selected_phrase)
			print conv_topic
			if selected_phrase.link_to_topic != "":
				conv_topic = selected_phrase.link_to_topic
			if selected_phrase.ends_conv == True:
				if player.conversation_partner.abstract == None:
					abstract = Abstract_Actor(player.conversation_partner)
					persistent_actors.append(abstract)
					player_phone.contacts.append(player.conversation_partner)
					print abstract.home.name
				player.conversation_partner.conversation_partner = None
				player.conversation_partner = None
				game_state = 'play'
	#Phone Menu Controls
	elif game_state == 'phone_window':
		menu_option = menu_control(player_phone.contacts, menu_option, key)
		if key.vk == libtcod.KEY_ENTER and len(player_phone.contacts) > 0:
			player_phone.contacts[menu_option].abstract.spawn(player.x, player.y-1)

	#General Controls
	#Movement keys
	elif key.vk == libtcod.KEY_UP:
		move_x = 0
		move_y = -1
	elif key.vk == libtcod.KEY_RIGHT:
		move_x = 1
		move_y = 0
	elif key.vk == libtcod.KEY_DOWN:
		move_x = 0
		move_y = 1
	elif key.vk == libtcod.KEY_LEFT:
		move_x = -1
		move_y = 0
	elif key.c == ord('.'):
		move_x = 0
		move_y = 0
	if move_x != None and move_y != None:
		if game_state == 'play':
			player.move(move_x, move_y)
			player.ai.timer = player.ai.timer_max
		elif game_state == 'look':
			cursor.move(move_x, move_y)
		elif game_state == 'conv_select':
			cursor.move(move_x, move_y)

	#Spawning items test.
	elif key.c == ord('D') and game_state == 'play':
		active_map.items.append(all_items['pickaxe'].copy(player.x, player.y))
	#Yield
	elif key.c == ord('Y') and game_state == 'play':
		player_cortex.combat_yield()
	#Suicide key.
	elif key.c == ord('H') and game_state == 'play':
		player.ai.death()
	#Create an agent.
	elif key.c == ord('A') and game_state == 'play':
		new_x = 0
		new_y = active_map.height
		while new_x <= 0 or new_y <= 0 or new_x >= active_map.width or new_y >= active_map.height:
			print new_x, new_y
			new_x = libtcod.random_get_int(0, player.x-10, player.x+10)
			new_y = libtcod.random_get_int(0, player.y-10, player.y+10)
		create_agent(new_x, new_y)
	#Spawn the location's inhabitant, if it has one.
	elif key.c == ord('S') and game_state == 'play':
		if active_map.inhabitant != None and active_map.actors.count(active_map.inhabitant.actor) == 0:
			active_map.inhabitant.spawn(15, 15)
	#View inventory.
	elif key.c == ord('i') and game_state == 'play':
		menu_option = 0
		current_list = player.abstract_inv
		game_state = 'inv_window'
	#View player info.
	elif key.c == ord('I') and game_state == 'play':
		game_state = 'info_window'
	#View abilities.
	elif key.c == ord('a') and game_state == 'play':
		game_state = 'ability_window'
	#View message backlog
	elif key.c == ord('m') and game_state == 'play':
		game_state = 'message_window'
	#Pick up items.
	elif key.c == ord('g') and game_state == 'play':
		if player.location != 'travel':
			player.pick_up()
			player.ai.timer = player.ai.timer_max
		else:
			message("You can't pick up items on the travel map!")
	#Put items away.
	elif key.c == ord('p') and game_state == 'play':
		for part in player.body.parts:
			if part.flags['grasps'] and part.item != None:
				player.abstract_inv.append(part.item)
				message('You put the ' + part.item.name + ' in your satchel.')
				part.item = None
				break
	#Drop items.
	elif key.c == ord('d') and game_state == 'play':
		if player.location != 'travel':
			menu_option = 0
			current_list = player.abstract_inv
			game_state = 'drop_window'
			player.ai.timer = player.ai.timer_max
		else:
			message("You can't drop items on the travel map!")
	#Enter Look mode.
	elif key.c == ord('l'):
		if game_state == 'play':
			active_map.actors.append(cursor)
			game_state = 'look'
			cursor.x = player.x
			cursor.y = player.y
		elif game_state == 'look':
			active_map.actors.remove(cursor)
			cursor.exit_tile()
			game_state = 'play'
	#Enter Conversation mode.
	elif key.c == ord('t'):
		if game_state == 'play':
			active_map.actors.append(cursor)
			game_state = 'conv_select'
			cursor.x = player.x
			cursor.y = player.y
		elif game_state == 'conv_select':
			active_map.actors.remove(cursor)
			cursor.exit_tile()
			game_state = 'play'
	#Select things!
	elif key.vk == libtcod.KEY_ENTER:
		if game_state == 'conv_select':
			for actor in active_map.actors:
				if actor != cursor and actor.x == cursor.x and actor.y == cursor.y and actor != player:
					player.conversation_partner = actor
					actor.conversation_partner = player
					game_state = 'conv_window'
					active_map.actors.remove(cursor)
					cursor.exit_tile()
					for actor in active_map.actors:
						print actor.name
					break
		elif game_state == 'look':
			available = active_map.map[cursor.x][cursor.y].contents
			for k in available:
				if k.type == 'cursor' or k.type == 'map':
					available.remove(k)
			if len(available) > 0:
				menu_option = 0
				game_state = 'look_window'
			else:
				active_map.actors.remove(cursor)
				cursor.exit_tile()
				game_state = 'play'
		elif game_state == 'look_window':
			pass
		elif game_state == 'look_focus_window':
			if key_buffer:
				key_buffer = False
			else:
				message("Done examining.")
				active_map.actors.remove(cursor)
				cursor.exit_tile()
				game_state = 'play'
	#Universal window exit.
	elif key.vk == libtcod.KEY_SPACE:
		if game_state.find('_window') != -1 or game_state == 'textbox':
			if active_map.actors.count(cursor) != 0:
				active_map.actors.remove(cursor)
				cursor.exit_tile()
			game_state = 'play'
	#Switch to the Travel map.
	elif key.c == ord('T'):
		if game_state == 'play' and active_map != travelmap:
			player.switch_map(travelmap, active_map.travel_x, active_map.travel_y)
			player.location = 'travel'
	#Go down stairs or enter a location on the Travel map.
	elif key.c == ord('>'):
		if active_map == travelmap:
			if travelmap.map[player.x][player.y].contents[0].type == 'map':
				target = travelmap.map[player.x][player.y].contents[0]
				player.switch_map(target, target.owner.doorx, target.owner.doory+3)
				player.location = target.owner
		else:
			for actor in active_map.actors:
				if actor.name == 'stairs down' and actor.x == player.x and actor.y == player.y:
					player.switch_map(active_map.owner.floors[active_map.owner.floors.index(active_map)-1], player.x, player.y)
					player.ai.timer = player.ai.timer_max
	#Go up stairs.
	elif key.c == ord('<'):
		if active_map != travelmap:
			for actor in active_map.actors:
				if actor.name == 'stairs up' and actor.x == player.x and actor.y == player.y:
					if active_map.owner.floors.index(active_map)+1 < len(active_map.owner.floors):
						player.switch_map(active_map.owner.floors[active_map.owner.floors.index(active_map)+1], player.x, player.y)
					player.ai.timer = player.ai.timer_max

def handle_mouse(): #!!BROKEN!!
	global active_map
	#Use the mouse to look at things, etc. !!BROKEN!!
	mouse = libtcod.mouse_get_status()
	(x, y) = (mouse.cx, mouse.cy)

	libtcod.console_set_foreground_color(panel2, libtcod.white)
	if active_map.map[x][y].blocked:
		libtcod.console_print_left(panel2, 2, 2, libtcod.BKGND_NONE, "Wall")
	else:
		libtcod.console_print_left(panel2, 2, 2, libtcod.BKGND_NONE, "Floor")

def menu_control(list, choice, key):
	#Handles easy control of menus, so that handle_keys doesn't have to.
	if key.vk == libtcod.KEY_UP:
		if choice == 0:
			choice = len(list)-1
		elif choice > 0:
			choice -= 1
	elif key.vk == libtcod.KEY_DOWN:
		if choice == len(list)-1:
			choice = 0
		elif choice < len(list)-1:
			choice += 1
	
	return choice

def text_input(panel, x, y, command = ""):
	libtcod.sys_set_fps(LIMIT_FPS)
	timer = 0
	entered = False
	orig_x = x
	w = libtcod.console_get_width(panel)
	h = libtcod.console_get_height(panel)
	
	while not entered:
		key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
		
		timer += 1
		if timer > LIMIT_FPS/2:
			libtcod.console_set_char(panel, x, y, "_")
			libtcod.console_set_fore(panel, x, y, libtcod.white)
			if timer == LIMIT_FPS:
				timer = 0
		else:
			libtcod.console_set_char(panel, x, y, " ")
			libtcod.console_set_fore(panel, x, y, libtcod.white)
		
		if key.vk == libtcod.KEY_BACKSPACE and x > 0:
			libtcod.console_set_char(panel, x, y, " ")
			libtcod.console_set_fore(panel, x, y, libtcod.white)
			command = command[:-1]
			if x > orig_x:
				x -= 1
		elif key.vk == libtcod.KEY_ENTER:
			libtcod.sys_set_fps(0)
			return command
		elif key.c > 0:
			letter = chr(key.c)
			libtcod.console_set_char(panel, x, y, letter)
			libtcod.console_set_fore(panel, x, y, libtcod.white)
			command += letter
			x += 1
		render_all()
		libtcod.console_flush()

#Item Script Functions

def script_phone():
	global game_state
	game_state = 'phone_window'

#Misc. Useful Functions

def is_blocked(x, y):
	global active_map
	if x > libtcod.console_get_width(active_map.con)-1:
		return True
	elif y > libtcod.console_get_height(active_map.con)-1:
		return True
	elif x < 0:
		return True
	elif y < 0:
		return True
	elif active_map.map[x][y].blocked == True:
		return True
	
	for blum in active_map.map[x][y].contents:
		if blum.blocks == True:
			return True
	
	else:
		return False

def create_agent(x, y):
	color = libtcod.Color(libtcod.random_get_int(0, 100, 254), libtcod.random_get_int(0, 100, 254), libtcod.random_get_int(0, 100, 254))
	newai = AI()
	if libtcod.random_get_int(0, 0, 1) == 0:
		gender = 'female'
	else:
		gender = 'male'
	newbody = BODIES[0].spawn_new()
	newagent = Actor(gen_name(gender), gender, x, y, color, 'U', newbody)
	newagent.plug_fighter(Fighter(newagent))
	newagent.plug_ai(newai)
	
	for att in newagent.attributes:
		newagent.attributes[att] += libtcod.random_get_int(0, -10, 10)
	
	active_map.items.append(all_items['pickaxe'].copy(newagent.x, newagent.y))
	newagent.frontal_cortex.claim_item(active_map.items[len(active_map.items)-1])
	active_map.actors.append(newagent)
	print "Map contains " + str(len(active_map.actors)) + " actors."
	return newagent

def create_offscreen_actor():
	color = random_color()
	newai = AI()
	if libtcod.random_get_int(0, 0, 1) == 0:
		gender = 'female'
	else:
		gender = 'male'
	newbody = BODIES[0].spawn_new()
	newagent = Actor(gen_name(gender), gender, 0, 0, color, 'U', newbody)
	newagent.plug_fighter(Fighter(newagent))
	newagent.plug_ai(newai)
	
	for att in newagent.attributes:
		newagent.attributes[att] += libtcod.random_get_int(0, -10, 10)
		
	return newagent

def vary_damage(force, reverb):
	#Calculate damage based on attack Force and Reverberation. Force is raw damage, Reverb is the amount of area it's spread over.
	#Really this just does a bit of random variation.
	force_mod = int(force/4)
	total_force = libtcod.random_get_int(0, force-force_mod, force+force_mod)
	reverb_mod = int(reverb/4)
	total_reverb = libtcod.random_get_int(0, reverb-reverb_mod, reverb+reverb_mod)
	return (total_force, total_reverb)

def random_color():
	color = libtcod.Color(libtcod.random_get_int(0, 50, 254), libtcod.random_get_int(0, 50, 254), libtcod.random_get_int(0, 50, 254))
	return color

def player_setup():
	global player, player_cortex, player_phone
	#Sets up the player object when New Game is selected.
	player_ai = Player_AI()
	player_body = BODIES[0].spawn_new()
	player = Actor('Unnamed', 'Ungendered', 4, 7, libtcod.violet, '@', player_body)
	player.plug_fighter(Fighter(player))
	player.plug_ai(player_ai)
	player.is_player = True
	player.location = 'travel'

	player_phone = Phone('cell phone', 0, 0, libtcod.light_grey, "'", script_phone)

	player.abstract_inv.append(player_phone)
	
	#set up brain
	player_cortex = Player_Cortex(player)
	
	active_map = travelmap
	active_map.actors = [player]

#Save Functions

def save_actors():
	save_write = open('data/save/saved_actors.txt', 'w')
	for actor in active_map.actors:
		print actor.name
		if actor.type == 'actor' and actor != player:
			save_write.write('NEW_ACTOR')
			save_write.write('name_' + actor.name + '\n')
			save_write.write('r_' + str(actor.color.r) + '\n')
			save_write.write('g_' + str(actor.color.g) + '\n')
			save_write.write('b_' + str(actor.color.b) + '\n')
			save_write.write('gender_' + actor.gender + '\n')
			save_write.write('\n')
	save_write.close()

def load_actors():
	global loaded_actors
	loaded_actors = []
	att_dict = {}
	lines = []
	load_file = open('data/save/saved_actors.txt', 'r')
	for line in load_file.lines:
		lines.append(line)
	load_file.close()
	for line in lines:
		if line == 'NEW_ACTOR':
			att_dict = {}

#Generative Functions

def setup_travelmap():
	global maps
	for k in maps:
		if k.on_travel_map:
			travelmap.map[k.travel_x][k.travel_y].contents.append(k)

def find_building_rect(tile):
	search_x = tile.x
	search_y = tile.y
	max_x = 0
	max_y = 0
	rect = []
	while travelmap.map[tile.x][search_y].color != colors.street:
		while travelmap.map[search_x][tile.y].color != colors.street:
			rect.append(travelmap.map[search_x][search_y])
			travelmap.map[search_x][search_y].is_in_building = True
			if search_x < travelmap.width-1:
				search_x += 1
				if search_x > max_x:
					max_x = search_x
		search_y += 1
		if search_y > max_y:
			max_y = search_y
		search_x = tile.x
	building = Building(tile.x, tile.y, max_x-1-tile.x, max_y-1-tile.y, rect)
	return building

def generate_city():
	global buildings
	#Start with the predone block of "grass" blocks.
	#Draw a border, to create some kind of strange enclosed city.
	street_x = 1
	street_y = 1
	while street_x < travelmap.width-2:
		travelmap.map[street_x][travelmap.height-2].color = colors.street
		travelmap.map[street_x][1].color = colors.street
		street_x += 1
	while street_y < travelmap.height-2:
		travelmap.map[travelmap.width-2][street_y].color = colors.street
		travelmap.map[1][street_y].color = colors.street
		street_y += 1
	travelmap.map[travelmap.width-2][travelmap.height-2].color = colors.street
	
	#Lopsided four-cell thing done! Draw streets down it in fourths now.
	#These being the vertical streets.
	street_x = travelmap.width/4
	street_y = 1
	while street_x < travelmap.width-5:
		while street_y < travelmap.height-2:
			travelmap.map[street_x][street_y].color = colors.street
			street_y += 1
		street_x += libtcod.random_get_int(0, (travelmap.width/4)-2, (travelmap.width/4)+2)
		street_y = 1
	#Do it for y!
	#These being the horizontal streets.
	street_x = 1
	street_y = travelmap.height/4
	while street_y < travelmap.width-5:
		while street_x < travelmap.width-2:
			travelmap.map[street_x][street_y].color = colors.street
			street_x += 1
		street_y += libtcod.random_get_int(0, (travelmap.height/4)-2, (travelmap.height/4)+2)
		street_x = 1
	
	#The street grid is done! This should be improved later, but for now it works.
	#Now, for buildings.
	building_tile_list = []
	for x in range(travelmap.width-2):
		for y in range(travelmap.height-2):
			if x != 0 and y != 0 and travelmap.map[x][y].color != colors.street:
				building_tile_list.append(travelmap.map[x][y])
	for tile in building_tile_list:
		tile.color = colors.building
		tile.blocked = True
	#Identifies buildings! :D
	for x in range(travelmap.width-2):
		for y in range(travelmap.height-2):
			if not travelmap.map[x][y].is_in_building and travelmap.map[x][y].color == colors.building:
				buildings.append(find_building_rect(travelmap.map[x][y]))
	
	#Links buildings to doorways to maps.
	for map in maps:
		if map != travelmap:
			for building in buildings:
				if building.claimed == False:
					building.claimed = True
					map.travel_x = libtcod.random_get_int(0, building.x+2, building.x+building.w-1)
					map.travel_y = building.y+building.h
					building.link = map
					travelmap.map[map.travel_x][map.travel_y].blocked = False
					travelmap.map[map.travel_x][map.travel_y].color = colors.travel_door
					map.on_travel_map = True
					break
	
	#Name places.
	for place in places:
		if place.name_gen_list != 'none':
			place.name = gen_name(place.name_gen_list)
		place.floors[0].name = place.name

def parse_everything():
	#Body Parser
	body_parse = libtcod.parser_new()
	#Structure Setup- Bodies, Limbs and Hubs.
	body_struct = libtcod.parser_new_struct(body_parse, "body_type")
	limb_struct = libtcod.parser_new_struct(body_parse, "new_limb")
	hub_struct = libtcod.parser_new_struct(body_parse, "new_hub")
	#Props for body_struct.
	#Has none.
	#Props for hub_struct.
	libtcod.struct_add_property(hub_struct, "parent", libtcod.TYPE_STRING, False)
	libtcod.struct_add_property(hub_struct, "size", libtcod.TYPE_INT, True)
	libtcod.struct_add_flag(hub_struct, "IMPORTANT")
	#Props for limb_struct.
	libtcod.struct_add_property(limb_struct, "parent", libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(limb_struct, "size", libtcod.TYPE_INT, True)
	libtcod.struct_add_flag(limb_struct, "VITAL")
	libtcod.struct_add_flag(limb_struct, "GRASPS")
	libtcod.struct_add_flag(limb_struct, "IMPORTANT")
	#Defining sub-structures.
	libtcod.struct_add_structure(body_struct, limb_struct)
	libtcod.struct_add_structure(body_struct, hub_struct)
	#Run.
	libtcod.parser_run(body_parse, "data/bodies.txt", BodyListener())
	libtcod.parser_delete(body_parse)
	
	#Place Parser
	place_parse = libtcod.parser_new()
	#Structure Setup!
	place_struct = libtcod.parser_new_struct(place_parse, "place_struct")
	#Properties!
	libtcod.struct_add_property(place_struct, "name", libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(place_struct, "total_size", libtcod.TYPE_INT, True)
	libtcod.struct_add_property(place_struct, "building_size", libtcod.TYPE_INT, True)
	libtcod.struct_add_property(place_struct, "floors", libtcod.TYPE_INT, True)
	libtcod.struct_add_property(place_struct, "spawn_rate", libtcod.TYPE_INT, True)
	libtcod.struct_add_property(place_struct, "name_gen_list", libtcod.TYPE_STRING, True)
	libtcod.struct_add_flag(place_struct, "SHOP_COUNTER")
	libtcod.struct_add_flag(place_struct, "CHECKERED_FLOOR")
	libtcod.struct_add_flag(place_struct, "QUEUE")
	libtcod.struct_add_flag(place_struct, "STAIRWELL")
	libtcod.struct_add_flag(place_struct, "LIVABLE")
	libtcod.struct_add_flag(place_struct, "SHOPKEEPER")
	#Run.
	libtcod.parser_run(place_parse, "data/places.txt", PlaceListener())
	libtcod.parser_delete(place_parse)
	
	#Item Parser
	item_parse = libtcod.parser_new()
	#Struct!
	item_struct = libtcod.parser_new_struct(item_parse, "item_struct")
	#Properties!
	libtcod.struct_add_property(item_struct, "name", libtcod.TYPE_STRING, False)
	libtcod.struct_add_property(item_struct, "char", libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(item_struct, "description", libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(item_struct, "damage_reverb", libtcod.TYPE_INT, False)
	libtcod.struct_add_property(item_struct, "damage_concentration", libtcod.TYPE_INT, False)
	libtcod.struct_add_property(item_struct, "weapon_skill", libtcod.TYPE_STRING, False)
	#Ain't none flags.
	#Run!
	libtcod.parser_run(item_parse, "data/items.txt", ItemListener())
	libtcod.parser_delete(item_parse)
	print all_items
	
	#Event Verb Parser
	verb_parse = libtcod.parser_new()
	#Struct
	verb_struct = libtcod.parser_new_struct(verb_parse, "verb_struct")
	#Flags
	libtcod.struct_add_flag(verb_struct, "POSSESSIVE")
	libtcod.struct_add_flag(verb_struct, "VIOLENT")
	libtcod.struct_add_flag(verb_struct, "SOCIAL")
	libtcod.struct_add_flag(verb_struct, "VISIBLE")
	#Run parse
	libtcod.parser_run(verb_parse, "data/verbs.txt", VerbListener())
	libtcod.parser_delete(verb_parse)
	
	#Conversation Topic Parser
	topic_parse = libtcod.parser_new()
	#Structs- Topic and Response.
	topic_struct = libtcod.parser_new_struct(topic_parse, "topic_struct")
	phrase_struct = libtcod.parser_new_struct(topic_parse, "phrase_struct")
	#Properties!
	#None.
	#Phrase properties!
	libtcod.struct_add_property(phrase_struct, "phrase_text", libtcod.TYPE_STRING, True)
	libtcod.struct_add_property(phrase_struct, "abs_opinion_change", libtcod.TYPE_INT, False)
	libtcod.struct_add_property(phrase_struct, "link_to_topic", libtcod.TYPE_STRING, False)
	libtcod.struct_add_property(phrase_struct, "phrase_id", libtcod.TYPE_STRING, True)
	#Sub-structs!
	libtcod.struct_add_structure(topic_struct, phrase_struct)
	#Run!
	libtcod.parser_run(topic_parse, "data/conv.txt", ConvListener())
	libtcod.parser_delete(topic_parse)

def gen_name(type):
	libtcod.namegen_parse('data/names.txt')
	name = libtcod.namegen_generate(type)
	libtcod.namegen_destroy()
	if name.count('FIRSTLAST') == 1:
		libtcod.namegen_parse('data/names.txt')
		if libtcod.random_get_int(0, 0, 1) == 0:
			first = libtcod.namegen_generate('male')
		else:
			first = libtcod.namegen_generate('female')
		name = first + ' ' + name.partition(' ')[2]
	elif name.count('LAST') == 1:
		libtcod.namegen_parse('data/names.txt')
		if libtcod.random_get_int(0, 0, 1) == 0:
			first = libtcod.namegen_generate('male')
		else:
			first = libtcod.namegen_generate('female')
		name = first.partition(' ')[2] + ' ' + name.partition(' ')[2]
	return name

########
#OBJECTS
########

#Map objects.
travelmap = Map('travelmap', 30, 30)
active_map = travelmap

maps = [travelmap]
places = []
buildings = []

#Cursor setup.
cursor = Cursor(0, 0, libtcod.light_yellow, 'X')

##########
#VARIABLES
##########

#Screen stuff.
SCREEN_W = 90
SCREEN_H = 60
LIMIT_FPS = 60
libtcod.sys_set_fps(0)

#GUI values- finding half the size of the screen, etc.
HALF_W = SCREEN_W/2
HALF_H = (SCREEN_H-2)/2
THIRD_W = SCREEN_W/3
THIRD_H = (SCREEN_H-2)/3
QUARTER_W = SCREEN_W/4
QUARTER_H = (SCREEN_H-2)/4

#Initialize the consoles! Including GUI panels.
libtcod.console_init_root(SCREEN_W, SCREEN_H, 'Dastardly Pre-Alpha v.24', False)
con = libtcod.console_new(SCREEN_W, SCREEN_H)
panel1 = libtcod.console_new(2*THIRD_W, 3*QUARTER_H)
panel2 = libtcod.console_new(2*THIRD_W, QUARTER_H+2)
panel3 = libtcod.console_new(THIRD_W, HALF_H)
panel4 = libtcod.console_new(THIRD_W, HALF_H)
window_panel = libtcod.console_new(3*QUARTER_W, 3*QUARTER_H)

panels = [panel1, panel2, panel3, panel4, active_map.con, window_panel]

#Menu Options and Variables
slide = 0
title_menu = ['New Game', 'Load Game', 'Exit (ESC)']
esc_menu = ['Back to Game', 'Quit to Title', 'Quit Game']
game_setup_menu = [('male', 'female'), 'TEXT']
persistent_actors = []

#Loading Variables.
BODIES = []
verbs = {}

#Gameplay Variables
game_state = 'open'
previous_state = 'play'
menu_option = 0
player_action = None
game_msgs = []
game_msgs_backlog = []
textbox_lines = []
conv_topic = 'intro'
conv_options = {'intro' : {"Let's talk about music." : 'music'}, 'music' : {}}
conv_topics = {}
all_items = {'phone' : Phone('cell phone', 0, 0, libtcod.light_grey, "'", script_phone)}

body_part_flags = {'grasps': False, 'important' : False, 'vital' : False, 'severed' : False}

#Pregame Logic
#Run the parsers and generate the city!
parse_everything()
print "done."
print "generating city..."
generate_city()
print "done."
setup_travelmap()

#Player setup.
player_setup()

#Declare list of actors in the scene.
active_map.actors = [player]

#Declare list of items in the scene.
active_map.items = []

while not libtcod.console_is_window_closed():
	#Clear the consoles! Clearing here allows us to print text in functions besides render_all(). A bit sloppy, but much easier in certain cases.
	for panel in panels:
		libtcod.console_clear(panel)
	
	if game_state != 'open': #Key buffer
		if game_state == 'play' and player.ai.timer == 0:
			player_action = handle_keys()
		elif game_state != 'play':
			player_action = handle_keys()
		#handle_mouse()
	elif game_state == 'open':
		game_state = 'title_menu'
	
	if game_state == 'look':
		cursor.describe()
	if game_state == 'play' and player.ai.timer != 0:
		for actor in active_map.actors:
			if actor.type == "actor":
				actor.frontal_cortex.decision()
		if player.location != 'travel':
			player.location.spawn_logic()
		active_map.update_events()
		for effect in active_map.effects:
			effect.effect_logic()
		#time.sleep((1/10))
	if game_state == 'play':
		player_cortex.decision()
	
	if player_action == 'exit':
		save_actors()
		break
	
	render_all()