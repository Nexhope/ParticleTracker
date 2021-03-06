import numpy as np
import random
import math
import os
import string
import sys

import System.Fileio as Fileio
import Detection.ctrack as ct
import Detection.detectParticles as dP

'''
This program creates multiple tracks of gaussian random walks. 

The input parameters are:
(D1, D2, D3, p12, p21, p13, p23, p31, p32,
 number of frame, number of particles, acquisition time, pixel array,
 wavelength, Pixel size, NA, magnification, S/N, Intensity)

The output parameters are:
All Tracks = [Track1,Track2,Track3,...]
Tracki = [Particle1, Particle2, ...]
Particle1 = [frame, dx, dy, x, y, state, Intensity, 
 Background, sigma_x, sigma_y, Particle ID]
'''

def debug(stringin):
    print(stringin)
    sys.stdout.flush()
    return


def simulateTracks(inVars=[],path=".",imageoutput=True):
    print(">>>Simulation starting")
    sys.stdout.flush()

    if not os.path.isdir(path):
        os.mkdir(path)

    if len(inVars) == 0:
        #Read in Values from file
        #sV = Fileio.getSysProps()
        print("Nothing in place for this case.")
        sys.exit()

    else:   
        #else read from input
        sV = list(inVars)
    #Diff constants of 3 states
    D = np.array([sV[1],sV[2],sV[3]])*1e-12
    #Markov probability matrix for state switching
    p = np.array([[1-(sV[4]+sV[6]),sV[4],sV[6]],[sV[5],1-(sV[5]+sV[7]),sV[7]],[sV[8],sV[9],1-(sV[8]+sV[9])]]) 
    #Number of frames
    frames = int(sV[10])
    #Number of particles
    N = int(sV[11])
    #Acquisition time
    tau = sV[12]
    #Number of pixels (side of square)
    numPixels = int(sV[13])
    #Other properties
    wavelength = sV[14]/1e9
    pixel_size = sV[15]/1e6
    print(pixel_size)
    numAperture = sV[16]
    background = sV[17]
    backnoise = sV[18]
    intensity = sV[19]
    if sV[20] == 0:
        blinkingBool = False
    else:
        blinkingBool = True
    particle_size = 1e-9 #meter
    print("Done with userInput")
    sys.stdout.flush()
    
    

    #Initial probabilities for choosing state
    '''
    pi1 = ( p21 + p31 ) / (p12 + p13 + p21 + p23 + p31 + p32)
    pi2 = ( p12 + p32 ) / (p12 + p13 + p21 + p23 + p31 + p32)
    pi3 = ( p13 + p23 ) / (p12 + p13 + p21 + p23 + p31 + p32)
    '''
    statProbs = []
    sumprobs = p[0,1] + p[1,0] + p[0,2] + p[2,0] + p[1,2] + p[2,1]
    if sumprobs == 0:
        statProbs = [0.5,0.5,0]
    else:
        statProbs.append((p[1,0] + p[2,0])/sumprobs)
        statProbs.append((p[0,1] + p[2,1])/sumprobs)
        statProbs.append((p[0,2] + p[1,2])/sumprobs)

    debug("Done probs init")

    #TODO: Blinking and Bleaching
    p_on = 0.3
    p_off = 0.1
     
    #output variable
    atracks = []
    btracks = []
    framelist = [ [] for i in range(frames)]
    for n in range(N):
        #one individual track
        track = []
        if blinkingBool:
            state_chain = [1]
            for i in range(1,frames,1):
                if state_chain[-1] == 1:
                    if p_off > random.uniform(0,1):
                        state_chain.append(0)
                    else:
                        state_chain.append(1)
                else:
                    if p_on > random.uniform(0,1):
                        state_chain.append(1)
                    else:
                        state_chain.append(0)
        else:
            state_chain = [1]*frames

        track_id = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        trk = ct.ParticleTrack(id=track_id, num_elements=frames)
     
        for i in range(0,frames,1):
     
            #particle in one frame
            particle = np.zeros((11))
     
            #frame number
            particle[0] = i

     
            #first or not?
            if len(track)  == 0:
                #initial position
                particle[3] = random.uniform(0,(numPixels-1)*1.*pixel_size)
                particle[4] = random.uniform(0,(numPixels-1)*1.*pixel_size)
     
                #choose state
                u = random.random()
                if u < statProbs[2]:
                    particle[5] = 2
                elif u < (statProbs[2] + statProbs[1]):
                    particle[5] = 1
                else:
                    particle[5] = 0
     
            else:
     
                #Calc new absolut position
                particle[3] = track[-1][3] + track[-1][1]
                particle[4] = track[-1][4] + track[-1][2]
     
                #choose new state
                u = random.random()
                s0 = int(track[-1][5])
                s1 = int((s0+1) % 3)
                s2 = int((s0+2) % 3)
                if u < p[s0,s2]:
                    particle[5] = s2
                elif u < (p[s0,s2] + p[s0,s1]):
                    particle[5] = s1
                else:
                    particle[5] = s0
     
            #Generate displacement in correct state
            particle[1] = random.gauss(0,math.sqrt(2*D[int(particle[5])]*tau))
            particle[2] = random.gauss(0,math.sqrt(2*D[int(particle[5])]*tau))

            #Set Intensity:
            particle[6] = intensity
            #particle width is n*0.211*lambda/NA; n = 1.51 for oil 1.33 for water, 1 for air
            particle[7] = 1.51*0.211*wavelength/numAperture
            particle[8] = 1.51*0.211*wavelength/numAperture
     
            #Rest of particle variables
            for k in range(9,10,1):
                particle[k] = 0

            particle[10] = n
     
            #Append particle to track
            track.append(particle)
            pfac = pixel_size
            prtcl = ct.makeParticle(i+1,particle[3]/pfac,particle[4]/pfac,particle[7]/pfac,particle[8]/pfac,background,particle[6],track_id)
            if state_chain[i] == 1:
                framelist[i].append(prtcl)            
            trk.insert_particle(prtcl,i+1)

        #Append Track to output var
        atracks.append(track)
        btracks.append(trk)
     
    #Print tracks to file
    #Fileio.setTrackFile(atracks,filename="simulatedTracks.txt")
    writeTracks(btracks,path+"/simulatedTracks.txt")
    debug("Written trajectory file")
    #frames = Fileio.tracksToFrames(atracks)
    #Fileio.setDetection(frames,filename="simulatedDetections.txt")
    writeFrames(framelist,path+"/simulatedFrames.txt")
    debug("Written particle file")

    if imageoutput:
        if particle_size < 0.61*wavelength/numAperture:
            #Sigma = n * 0.211* lambda/NA; n = index of refraction (1.51 in oil, 1.33 in water, 1 in air)
            Fileio.createImages(path,framelist,numPixels,
                    1.00*0.211*wavelength/numAperture/pixel_size,background,backnoise)
        else:
            pass
    debug("Written output Images")

    return framelist,btracks

def writeTracks(tracks,filename):
    ct.writeTrajectories(tracks,filename=filename)
    #ct.writeTracks(tracks,filename=filename)
    return

def writeFrames(framelist,filename):
    outframes = open(filename,'w')
    count = 1
    for frame in framelist:
        dP.writeDetectedParticles([frame,0],count,outframes)
        count += 1
    return

