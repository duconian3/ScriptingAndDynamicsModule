import maya.cmds as cmds
import maya.mel as mel
import math
import random

# GLOBAL VARIABLES
#
# These are variables the are used across more than one function
# e.g. last_frame_number is used in the init function and the run function
# when we want to use these variables in a function we need to indicate it is in fact
# a global variable using the global keyword

# last_frame_number stores the frame number of the last successful run of the simulation
# this is needed to prevent any odd behaviour if the timeline is played backwards
# or if we jump to a particular frame.
# we need to simulate every frame so we don't miss any events
last_frame_number = 1

#store the agents
agents = []

#the distance to determine if an agent is nearby
agent_near_distance = 5
enemy_near_distance = 7
#the distance to determine if an agent is close enough to hit
agent_hit_distance = 2 # random range just now

separation_weight = 0.15
cohesion_weight = 0.1
alignment_weight = 0.35
target_weight = 0.35 #hard set just now
seeking_weight = 0.35 

# this function is used to initialise the simulation
def init():
    print "Custom simulation initialised"
    # reset last frame counter
    global last_frame_number
    last_frame_number = 1
    
    find_agents_in_scene()
    global agents
    for agent in agents:
        agent_setup(agent)
        cmds.setAttr(agent+".state", 1)
    
# this function is called every frame the simulation is run
def run(frame_number):

    # get the frame rate by using an internal MEL script
    frame_rate = mel.eval("currentTimeUnitToFPS")

    # calculate the amount of time in seconds between each frame
    frame_time = 1.0 / frame_rate
    
    # special case if we are on the first frame then initialise the simulation
    if frame_number == 1:
        init()
        
    # check to see if we have an event to process this frame
    global last_frame_number
    if (frame_number - last_frame_number) == 1:

        global agents
        global agent_near_distance
        
        for agent in agents:
            
            #find the agents current Stats
            find_morale_status(agent)
            State = cmds.getAttr(agent+".state")
            Health = cmds.getAttr(agent+".health")
            closest_enemy = find_nearest_enemy_target(agent)
            
            #check to see if the agent is wounded enough to flee or is defeated
            if (Health > 0)and(Health < 20):
                State = 4
            elif(Health < 1):
                State = 0                
            
            #if moving towards target
            if State == 1: 
                do_flocking_behaviour(agent)
                agent_move(agent, frame_time)
            #if enemy is within charge distance
            elif State == 2:
                agent_rush(agent, closest_enemy)
                agent_move(agent, frame_time)
            #if fighting an enemy
            elif State == 3:
                print ""+str(agent)+" is attacking"
                agent_fight(agent, closest_enemy)
            #if fleeing
            elif State == 4:
                print "run away "+str(agent)
                agent_flee(agent, closest_enemy)
            #if defeated
            elif State == 0:
                print "unconscious "+str(agent)
                #scale = 1/3 and no other behaviours
                cmds.setAttr(agent+".scaleX", 0.33333)
                cmds.setAttr(agent+".scaleY", 0.33333)
                cmds.setAttr(agent+".scaleZ", 0.33333)
                #affect_team_morale_status(agent)
                
        print "Custom simulation run successfully at frame: "+str(frame_number)
        
        # we have successfully completed a run of the simulation
        # update the last frame number
        last_frame_number = frame_number

# ADD ANY OF YOUR OWN SCRIPT FUNCTIONS BELOW HERE #
def agent_setup(agent_name):

    # set the initial position
    if cmds.objExists(agent_name+".initialPositionX") is False:
        cmds.addAttr(agent_name, longName="initialPositionX", defaultValue=0.0, keyable=True)
        cmds.setAttr(agent_name+".initialPositionX", cmds.getAttr(agent_name+".translateX"))
    if cmds.objExists(agent_name+".initialPositionY") is False:
        cmds.addAttr(agent_name, longName="initialPositionY", defaultValue=0.0, keyable=True)
        cmds.setAttr(agent_name+".initialPositionY", cmds.getAttr(agent_name+".translateY"))
    if cmds.objExists(agent_name+".initialPositionZ") is False:
        cmds.addAttr(agent_name, longName="initialPositionZ", defaultValue=0.0, keyable=True)
        cmds.setAttr(agent_name+".initialPositionZ", cmds.getAttr(agent_name+".translateZ"))
    
    cmds.setAttr(agent_name+".translateX", cmds.getAttr(agent_name+".initialPositionX"))
    cmds.setAttr(agent_name+".translateY", cmds.getAttr(agent_name+".initialPositionY"))
    cmds.setAttr(agent_name+".translateZ", cmds.getAttr(agent_name+".initialPositionZ"))
    
    cmds.setAttr(agent_name+".scaleX", 1.0)
    cmds.setAttr(agent_name+".scaleY", 1.0)
    cmds.setAttr(agent_name+".scaleZ", 1.0)
    
    #set the initial heading
    if cmds.objExists(agent_name+".initialHeading") is False:
        cmds.addAttr(agent_name, longName="initialHeading", defaultValue=0.0, keyable=True)
        cmds.setAttr(agent_name+".initialHeading", cmds.getAttr(agent_name+".rotateY"))
        
    # setts the cone to point in the direction of the heading
    cmds.setAttr(agent_name+".rotateY", cmds.getAttr(agent_name+".initialHeading"))

    if cmds.objExists(agent_name+".initialSpeed") is False:
        cmds.addAttr(agent_name, longName="initialSpeed", defaultValue=1.0, keyable=True)
    if cmds.objExists(agent_name+".speed") is False:
        cmds.addAttr(agent_name, longName="speed", defaultValue=cmds.getAttr(agent_name+".initialSpeed"), keyable=True)
        cmds.setAttr(agent_name+".speed", cmds.getAttr(agent_name+".initialSpeed"))
        
    #if leader, the value will be 1, else 0 # think binary bool
    if cmds.objExists(agent_name+".leader") is False:
        cmds.addAttr(agent_name, longName="leader", defaultValue=0.0, keyable=True)        
    if cmds.objExists(agent_name+".team") is False:
        cmds.addAttr(agent_name, longName="team", defaultValue=1.0, keyable=True)
        
    if cmds.objExists(agent_name+".state") is False:
        cmds.addAttr(agent_name, longName="state", defaultValue=1.0, keyable=True)
    
    if cmds.objExists(agent_name+".health") is False:
        cmds.addAttr(agent_name, longName="health", defaultValue=100.0, keyable=True)
    val = random.randint(70,100)
    cmds.setAttr(agent_name+".health", val)
    if cmds.objExists(agent_name+".strength") is False:
        cmds.addAttr(agent_name, longName="strength", defaultValue=50.0, keyable=True)
    val = random.randint(5,20)
    cmds.setAttr(agent_name+".strength", val)            
    
    if cmds.objExists(agent_name+".morale") is False:
        cmds.addAttr(agent_name, longName="morale", defaultValue=10.0, keyable=True)
        
    if cmds.objExists(agent_name+".discipline") is False:
        cmds.addAttr(agent_name, longName="discipline", defaultValue=10.0, keyable=True)
    val = random.randint(5,10)
    cmds.setAttr(agent_name+".morale", val)
    
    if cmds.objExists(agent_name+".teamMorale") is False:
        cmds.addAttr(agent_name, longName="teamMorale", defaultValue=100.0, keyable=True)
        
    if cmds.objExists(agent_name+".battleNegatives") is False:
        cmds.addAttr(agent_name, longName="battleNegatives", defaultValue=0.0, keyable=True)
    
def agent_move(agent_name, frame_time):
    # get the heading angle
    heading = cmds.getAttr(agent_name+".rotateY");
    
    # get the speed (in units per second)
    speed = cmds.getAttr(agent_name+".speed")
    
    # calculate the overall distance moved between frames
    overall_distance = speed*frame_time
    
    # calculate the direction to go in # using trigonometry
    distanceX = overall_distance*math.sin(math.radians(heading));
    distanceZ = overall_distance*math.cos(math.radians(heading));

    # update the position based on the calculated direction and speed
    cmds.setAttr(agent_name+".translateX", cmds.getAttr(agent_name+".translateX")+distanceX)
    cmds.setAttr(agent_name+".translateZ", cmds.getAttr(agent_name+".translateZ")+distanceZ)

def find_agents_in_scene():
    global agents
    agents = cmds.ls("agent*", transforms=True)

def get_agent_position(agent_name):
    position = []
    position.append(cmds.getAttr(agent_name+".translateX"))
    position.append(cmds.getAttr(agent_name+".translateY"))
    position.append(cmds.getAttr(agent_name+".translateZ"))
    return position
    
def get_target_position(target_name):
    tar_pos = []
    tar_pos.append(cmds.getAttr(target_name+".translateX"))
    tar_pos.append(cmds.getAttr(target_name+".translateY"))
    tar_pos.append(cmds.getAttr(target_name+".translateZ"))
    return tar_pos
    
def get_agent_heading(agent_name):
    return cmds.getAttr(agent_name+".rotateY")
    
def set_agent_heading(agent_name, heading):
    cmds.setAttr(agent_name+".rotateY", heading)
    
def get_agent_heading_vector(agent_name):
    # get agent heading angle
    heading_angle = cmds.getAttr(agent_name+".rotateY")
    
    # convert heading angle to a heading vector
    heading_vector = get_vector_from_heading_angle(heading_angle)
    
    return heading_vector
    
def get_vector_from_heading_angle(heading):
    vector = []
    vector.append(math.sin(math.radians(heading)))
    vector.append(0)
    vector.append(math.cos(math.radians(heading)))
    return vector
            
def get_heading_angle_from_vector(vector):
    return math.degrees(math.atan2(vector[0], vector[2]))
    
def vector_add(vectorA, vectorB):
    result = []
    result.append(vectorA[0]+vectorB[0])
    result.append(vectorA[1]+vectorB[1])
    result.append(vectorA[2]+vectorB[2])
    return result
    
def vector_subtract(vectorA, vectorB):
    result = []
    result.append(vectorA[0]-vectorB[0])
    result.append(vectorA[1]-vectorB[1])
    result.append(vectorA[2]-vectorB[2])
    return result
    
def vector_scale(vector, scale):
    result = []
    result.append(vector[0]*scale)
    result.append(vector[1]*scale)
    result.append(vector[2]*scale)
    return result
    
def get_vector_between_points(pointA, pointB):
    vector = []
    vector.append(pointB[0] - pointA[0])
    vector.append(pointB[1] - pointA[1])
    vector.append(pointB[2] - pointA[2])
    return vector

def get_vector_length(vector):
    return math.sqrt(vector[0]*vector[0]+vector[1]*vector[1]+vector[2]*vector[2])
    
def vector_normalise(vector):
    vector_length = get_vector_length(vector)
    result = []
    if vector_length > 0.0:
        result.append(vector[0] / vector_length)
        result.append(vector[1] / vector_length)
        result.append(vector[2] / vector_length)
    else:
        result.append(vector[0])
        result.append(vector[1])
        result.append(vector[2])
    return result

def get_distance_between_points(pointA, pointB):
    return get_vector_length(get_vector_between_points(pointA, pointB))
    
#called in run # if no enemies near
def do_flocking_behaviour(agent):
    #for agent in agents:
    global agent_near_distance
    
    team = cmds.getAttr(agent+".team")
        
    #find the agents close by
    neighbours = find_agents_within_distance(agent, agent_near_distance) 
    
    enemy_within_range = find_nearest_enemy_target(agent)
    ##Aura calc hear or new function
        
    #only get a new heading if there are any agents close by
    if len(neighbours):
        
        for neighbour in neighbours:
            
            #find the team of the neighbours 
            team_Mate = cmds.getAttr(neighbour+".team")
            
            #if there is not a neighbour who is the closest enemy
            if neighbour != enemy_within_range:                     
                
                primary_target = "target_main"
                agent_heading_vector = get_flocking_heading(agent, neighbours, primary_target)
                
            else :
                cmds.setAttr(agent+".state",2)
                print ""+str(agent)+" state = 2"                         
           
        #we now have the desired heading
        #we'll just set our heading to it for now
        #better to stear nicely towards it
        agent_heading_angle = get_heading_angle_from_vector(agent_heading_vector)
        set_agent_heading(agent, agent_heading_angle)
        
def get_flocking_heading(agent_name, neighbours, primary_target):
    # initialise the heading vector for this agent
    heading_vector = [0, 0, 0]    
    
    global agent_hit_distance
    # apply the weighting to each heading vector and then add them altogether
    # to get the overall heading vector
    global separation_weight
    global cohesion_weight
    global alignment_weight
    global target_weight
    
    cohesion_heading_vector = get_cohesion_heading(agent_name, neighbours)
    cohesion_heading_vector = vector_scale(cohesion_heading_vector, cohesion_weight)
    heading_vector = vector_add(heading_vector, cohesion_heading_vector)
    
    alignment_heading_vector = get_alignment_heading(agent_name, neighbours)
    alignment_heading_vector = vector_scale(alignment_heading_vector, alignment_weight)
    heading_vector = vector_add(heading_vector, alignment_heading_vector)
    
    separation_heading_vector = get_separation_heading(agent_name, neighbours)
    separation_heading_vector = vector_scale(separation_heading_vector, separation_weight)
    heading_vector = vector_add(heading_vector, separation_heading_vector)
          
    ######targeting
    target_heading_vector = get_target_heading(agent_name, primary_target)
    target_heading_vector = vector_scale(target_heading_vector, target_weight)
    heading_vector = vector_add(heading_vector, target_heading_vector)
    
    return heading_vector
    
def agent_rush(agent_name,closest_enemy_name):
    print ""+str(agent_name)+" is rushing"
    heading_vector = [0, 0, 0] 
    global agent_hit_distance
    
    #find the position of the agent and enemy
    agent_position = get_agent_position(agent_name)
    enemy_position = get_agent_position(closest_enemy_name)
    print ""+str(agent_name)+" closest target is "+str(closest_enemy_name)
    
    #calculate the distance between the closest enemy and the agent
    enemy_gap = get_distance_between_points(agent_position, enemy_position)
    if(enemy_gap > agent_hit_distance):
        #set the enemy agent as the target 
        seeking_heading_vector = get_seeking_heading(agent_name, closest_enemy_name)
        seeking_heading_vector = vector_scale(seeking_heading_vector, seeking_weight)
        heading_vector = vector_add(heading_vector, seeking_heading_vector)
    else:
        #set the agent to fight
        cmds.setAttr(agent_name+".state",3)
        #print ""+str(agent_name)+" can hit now"
    
    agent_heading_angle = get_heading_angle_from_vector(heading_vector)
    set_agent_heading(enemy_target, agent_heading_angle)
        
def find_nearest_enemy_target(agent_name):
    global enemy_target
    
    team = cmds.getAttr(agent_name+".team")
    agent_position = get_agent_position(agent_name)
    
    closest_enemy_gap = 9999999
    
    for agent in agents:
        #check if the agent is an enemy that is alive
        if ((cmds.getAttr(agent+".team") != team)and(cmds.getAttr(agent+".state") != 0)):
            enemy_position = get_agent_position(agent)
            enemies_gap = get_distance_between_points(agent_position, enemy_position)
            #if the distance from checking agent to enemy agent 
            if(enemies_gap < closest_enemy_gap):
                closest_enemy_gap = enemies_gap
                enemy_target = agent
    return enemy_target  

def find_agents_within_distance(agent_name, distance):
    # neighbours is a list that will contain a list of nearby agents
    neighbours = []
    
    # get the position and team of the agent called agent_name
    agent_position = get_agent_position(agent_name)
    # FOR every agent in the agents list
    for agent in agents:
        # get the agent position of the potential neighbour
        neighbour_position = get_agent_position(agent)
        # calculate the distance between the potential neighbour and the agent called agent_name
        agents_gap = get_distance_between_points(agent_position, neighbour_position)
        # if this distance is less than distance passed into the function [this is the distance that defines 
        #the agent "awareness circle"] then add it to the neighbours list
        if(agents_gap < distance):
            neighbours.append(agent)
        
    return neighbours
    
    #, primary_target
def get_alignment_heading(agent_name, neighbours):
    # initialise the heading vector that will hold the alignment heading
    alignment_heading_vector = [0, 0, 0]    
    # get the number of neighbouring agents in the neighbours list [find the length of the list]
    num_neighbours = len(neighbours)
    #IF we have 1 or more agents in the neighbours list
    if (num_neighbours >= 1):
        #FOR every neighbour in the neighbours list
        for neighbour in neighbours:
            #get the heading of the neighbour as a vector
            neighbour_heading_vector = get_agent_heading_vector(neighbour)
            #add this heading to the alignment_heading_vector
            alignment_heading_vector = vector_add(alignment_heading_vector, neighbour_heading_vector)
        # calculate the averaged alignment_heading_vector
        alignment_heading_vector[0] = alignment_heading_vector[0] / num_neighbours
        alignment_heading_vector[1] = alignment_heading_vector[1] / num_neighbours
        alignment_heading_vector[2] = alignment_heading_vector[2] / num_neighbours
        # normalise alignment vector
        alignment_heading_vector = vector_normalise(alignment_heading_vector)

    return alignment_heading_vector

def get_separation_heading(agent_name, neighbours):
    # initialise the heading vector that will hold the separation heading
    separation_heading_vector = [0, 0, 0]

    # get the number of neighbouring agents in the neighbours list [find the length of the list]
    num_neighbours = len(neighbours)
    #IF we have 1 or more agents in the neighbours list
    if (num_neighbours >= 1):
        # get the position of the agent called agent_name
        agent_name_position = get_agent_position(agent_name)
        #FOR every neighbour in the neighbours list
        for neighbour in neighbours:
            # get the position of the neighbour
            neighbour_position = get_agent_position(neighbour)
            # calculate the heading vector from the neighbours position to the position of the agent called agent_name
            heading_vector = get_vector_between_points(agent_name_position, neighbour_position)
            #heading_vector = get_agent_heading_vector(agent_name)##??
            # normalise the heading vector to give it a size of 1 [needed to averaging the vector will work as expected]
            heading_vector = vector_normalise(heading_vector)
            # add this heading vector to the separation_heading_vector
            separation_heading_vector = vector_subtract(separation_heading_vector, heading_vector)
        # calculate the averaged separation_heading_vector
        separation_heading_vector[0] = separation_heading_vector[0] / num_neighbours
        separation_heading_vector[1] = separation_heading_vector[1] / num_neighbours
        separation_heading_vector[2] = separation_heading_vector[2] / num_neighbours
        #normalise the separation_heading_vector
        separation_heading_vector = vector_normalise(separation_heading_vector)

    return separation_heading_vector

def get_cohesion_heading(agent_name, neighbours):
    # initialise the heading vector that will hold the separation heading
    cohesion_heading_vector = [0, 0, 0]
    
    # get the number of neighbouring agents in the neighbours list [find the length of the list]
    num_neighbours = len(neighbours)
    #IF we have 1 or more agents in the neighbours list
    if (num_neighbours >= 1):
        # get the position of the agent called agent_name
        agent_name_position = get_agent_position(agent_name)
        # initialise a vector to hold the average of all the neighbours positions to [0, 0, 0]
        average_neighbours_position = [0, 0, 0]
        #FOR every neighbour in the neighbours list
        for neighbour in neighbours:
            # get the neighbours position
            neighbours_position = get_agent_position(neighbour)
            # add it to the vector to hold the average positions
            average_neighbour_position = vector_add(average_neighbours_position, neighbours_position)
        # calculate the averaged neighbours position
        average_neighbours_position[0] = average_neighbour_position[0] / num_neighbours
        average_neighbours_position[1] = average_neighbour_position[1] / num_neighbours
        average_neighbours_position[2] = average_neighbour_position[2] / num_neighbours
        # calculate the cohesion_heading_vector from the position of the agent called agent_name to 
        # the averaged neighbours position
        cohesion_heading_vector = get_vector_between_points(agent_name_position, average_neighbour_position)
        # normalise the cohesion_heading_vector
        cohesion_heading_vector = vector_normalise(cohesion_heading_vector)
    
    return cohesion_heading_vector
    
#copied from alignment
def get_target_heading(agent_name, primary_target):
    ##trig : currentpos = targetPosX/Y - previousPosX/Y
    
    # initialise the heading vector that will hold the target heading
    target_heading_vector = [0, 0, 0]
    
    target_Pos = get_target_position(primary_target)
    agent_Pos = get_agent_position(agent_name)
    
    target_distance = get_distance_between_points(agent_Pos, target_Pos)
    
    #if the agent hasn't already reached their target
    if target_Pos != agent_Pos:        
        current_Pos = vector_subtract(target_Pos,agent_Pos)#trig
    
        target_heading_vector = vector_add(target_heading_vector, current_Pos)        
        # normalise target vector
        target_heading_vector = vector_normalise(target_heading_vector)

    return target_heading_vector
    
#copied from target
def get_seeking_heading(agent_name, primary_target):
    ##trig : currentpos = targetPosX/Y - previousPosX/Y
    
    # initialise the heading vector that will hold the seeking heading
    seeking_heading_vector = [0, 0, 0]
    
    target_Pos = get_target_position(primary_target)
    agent_Pos = get_agent_position(agent_name)
    
    target_distance = get_distance_between_points(agent_Pos, target_Pos)
    
    #have distance fighting in here
    current_Pos = vector_subtract(target_Pos,agent_Pos)
    #changed from add to sub
    seeking_heading_vector = vector_subtract(seeking_heading_vector, current_Pos)
        
    # normalise seeking vector
    seeking_heading_vector = vector_normalise(seeking_heading_vector)

    return seeking_heading_vector

def agent_fight(agent_name, closest_enemy_name):
    global agent_hit_distance    
    
    #get the strength of the agent
    agent_strength = cmds.getAttr(agent_name+".strength")
    #get the health of the enemy
    enemy_health = cmds.getAttr(closest_enemy_name+".health")
    #print ""+str(agent_name)+" is attacking " +closest_enemy_name
    
    #while the agent is not defeated
    if(cmds.getAttr(agent_name+".state") != 0):
        #if the enemy's health has not been depleted
        if(enemy_health > 0):       
            #every frame subtract the players strength from the enemies health
            cmds.setAttr(closest_enemy_name+".health", enemy_health - agent_strength)
        else:
            #print ""+str(agent_name)+" defeated "+str(closest_enemy_name)
            # defeat the enemy
            cmds.setAttr(closest_enemy_name+".state", 0)
            # set the agent back to flocking
            cmds.setAttr(agent_name+".state", 1)

def agent_flee(agent_name,closest_enemy_name):
    #print ""+str(agent_name)+" is fleeing"
    heading_vector = [0, 0, 0] 
    
    #find_nearest_enemy_target(agent_name) # returns enemy_target
    enemy_position = get_agent_position(closest_enemy_name)
    #print ""+str(agent_name)+" closest target is "+str(closest_enemy_name)
    
    #set the enemy agent as the target 
    target_heading_vector = get_target_heading(agent_name, closest_enemy_name)
    target_heading_vector = vector_scale(target_heading_vector, seeking_weight)
    heading_vector = vector_add(heading_vector, target_heading_vector)
    
    agent_heading_angle = get_heading_angle_from_vector(heading_vector)
    set_agent_heading(enemy_target, agent_heading_angle)


def reset_agent_positions():
    global agents
    agents = cmds.ls("agent*", transforms=True)
    
    for agent_name in agents:
        if cmds.objExists(agent_name+".initialPositionX") is False:
            cmds.addAttr(agent_name, longName="initialPositionX", defaultValue=0.0, keyable=True)
        if cmds.objExists(agent_name+".initialPositionY") is False:
            cmds.addAttr(agent_name, longName="initialPositionY", defaultValue=0.0, keyable=True)
        if cmds.objExists(agent_name+".initialPositionZ") is False:
            cmds.addAttr(agent_name, longName="initialPositionZ", defaultValue=0.0, keyable=True)
        
        cmds.setAttr(agent_name+".initialPositionX", cmds.getAttr(agent_name+".translateX"))
        cmds.setAttr(agent_name+".initialPositionY", cmds.getAttr(agent_name+".translateY"))
        cmds.setAttr(agent_name+".initialPositionZ", cmds.getAttr(agent_name+".translateZ"))        

        if cmds.objExists(agent_name+".initialHeading") is False:
            cmds.addAttr(agent_name, longName="initialHeading", defaultValue=0.0, keyable=True)
        cmds.setAttr(agent_name+".initialHeading", cmds.getAttr(agent_name+".rotateY"))

        if cmds.objExists(agent_name+".initialSpeed") is False:
            cmds.addAttr(agent_name, longName="initialSpeed", defaultValue=1.0, keyable=True)
        if cmds.objExists(agent_name+".speed") is False:
            cmds.addAttr(agent_name, longName="speed", defaultValue=cmds.getAttr(agent_name+".initialSpeed"), keyable=True)
        cmds.setAttr(agent_name+".initialSpeed", cmds.getAttr(agent_name+".speed"))                
        if cmds.objExists(agent_name+".leader") is False:
            cmds.addAttr(agent_name, longName="leader", defaultValue=0.0, keyable=True)            
        if cmds.objExists(agent_name+".team") is False:
            cmds.addAttr(agent_name, longName="team", defaultValue=1.0, keyable=True)
        if cmds.objExists(agent_name+".state") is False:
            cmds.addAttr(agent_name, longName="state", defaultValue=1.0, keyable=True)
        if cmds.objExists(agent_name+".health") is False:
            cmds.addAttr(agent_name, longName="health", defaultValue=100.0, keyable=True)
        if cmds.objExists(agent_name+".strength") is False:
            cmds.addAttr(agent_name, longName="strength", defaultValue=50.0, keyable=True)            
        if cmds.objExists(agent_name+".morale") is False:
            cmds.addAttr(agent_name, longName="morale", defaultValue=10.0, keyable=True)


def find_morale_status(agent_name):
    
    discipline = cmds.getAttr(agent_name+".discipline")
    team_morale = cmds.getAttr(agent_name+".teamMorale")
    battleNegatives = cmds.getAttr(agent_name+".battleNegatives")
    
    agent_morale = (discipline + (team_morale * 0.1)) - battleNegatives
    
    cmds.setAttr(agent_name+".morale", agent_morale)
    #print ""+str(agent_name)+" morale is "+str(agent_morale)
    
    if agent_morale < 1:
        cmds.setAttr(agent_name+".morale", 4)






