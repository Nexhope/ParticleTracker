#================================
#=== Hidden Markov Model MCMC   
#================================

'''Done after the paper of Das (2009)
Using displacements {dr} of a track of length N to determine D1, D2, p12,
p21 of heterogeneous brownian motion.'''

#Packages
import numpy as np
import math
import random
import Fileio
import sys


np.seterr()
#Global variables
dr = np.array(Fileio.getTrackFile())[0][:,[1,2]]
tau = 0.1  #Acquisition time in s

#Helpful variables
logtau = math.log(4*math.pi*tau)
logten = math.log(10)

dr2 = np.zeros((len(dr)))
for i in range(len(dr)):
    dr2[i] = dr[i,0]*dr[i,0] + dr[i,1]*dr[i,1]
'''
print dr2
print
'''

# Functions
#-----------

#log(e^a+e^b)
def logsum(a,b):
    if a < -700 and b < -700:
        return -100000000
    elif a > 700 or b > 700:
        return -100000000
    return math.log(math.exp(a)+math.exp(b))

#Log-Likelyhood
def logLikelyhood(theta):
    #Preliminary variable calculations
    D = [10**theta[0],10**theta[1]]
    #logp = [math.log(theta[2]), math.log(theta[3])]
    pi = [theta[3]/(theta[2]+theta[3]),theta[2]/(theta[2]+theta[3])]
    #logpi = [math.log(pi[0]),math.log(pi[1])]

    #single step likelyhoods
    l = []
    for step in dr2:
        elem = []
        for i in range(2):
            elem.append(0 - step/(4*D[i]*tau) - logten * theta[i] - logtau)
        l.append(elem[:])
        


    #combining log-likelyhoods:
    alogs = []
    anew = []
    try:
        anew.append(math.log(pi[0])+l[0][0])
        anew.append(math.log(pi[1])+l[0][1])
    except ValueError:
        print(("pi is "+str(pi[0])+ ' ' + str(pi[1])))
        sys.exit(1)
    alogs.append(anew[:])

    for j in range(1,len(dr2)):
        #print j
        anew[0] = logsum(alogs[-1][0]+math.log(1-theta[2]), alogs[-1][1]+math.log(theta[3])) + l[j][0]
        anew[1] = logsum(alogs[-1][0]+math.log(theta[2]), alogs[-1][1]+math.log(1-theta[3])) + l[j][1]
        alogs.append(anew[:])
    return logsum(alogs[-1][0], alogs[-1][1])

def likelihood(theta):
    D = [theta[0],theta[1]]
    pi = [theta[3]/(theta[2]+theta[3]), theta[2]/(theta[2]+theta[3])]
    
    l = []
    for step in dr2:
        elem = np.zeros((2),dtype=np.float64)
        for i in range(len(D)):
            elem[i] = math.exp(-step/(4*D[i]*tau))/(4*math.pi*D[i]*tau)
        l.append(elem[:])


    anolog = []
    anew = np.zeros((2),dtype=np.float64)
    anew[0] = (pi[0]*l[0][0])
    anew[1] = (pi[1]*l[0][1])
    anolog.append(1.0*anew[:])

    for j in range(1,len(dr2)):
        anew = np.zeros((2),dtype=np.float64)
        anew[0] = ( anolog[-1][0]*(1-theta[2]) + anolog[-1][1]*theta[3] ) * l[j][0]
        #print anew[0].dtype
        anew[1] = ( anolog[-1][1]*(1-theta[3]) + anolog[-1][0]*theta[2] ) * l[j][1]
        anolog.append(1.0*anew)

    #print D
    #print theta
    #for k in range(len(l)):
    #    if l[k][0] > 1 or l[k][0] < 0:
    #        print 0, dr2[k], l[k][0]
    #    if l[k][1] > 1 or l[k][1] < 0:
    #        print 1, dr2[k], l[k][1]
    #print anolog[-1]
    return (anolog[-1][0]+anolog[-1][1])


def doMetropolis(logLikelyhood):
    N = 100000
    theta = []
    L = []
    vartheta = [1,1.0,0.0,0.0]
    theta.append(np.array([10,5,0.3,0.3]))
    proptheta = theta[-1][:]
    L.append(logLikelyhood(proptheta))
    Lmax = L[-1]
    
    outfile = open("hiddenMCMC.txt",'w')
    outfile.write("#Hidden Markov Chain Monte Carlo\n")
    outfile.write("# LogLikelyhood   log10(D1)  log10(D2)   p12   p21\n")

    for i in range(int(N/4)):
        for k in range(4):
            dt = np.zeros((4))
            l = 4 * i + k
            print(l)
            dt[k] = random.gauss(0, vartheta[k])
            if k in [2,3]:
                while proptheta[k] + dt[k] <= 0 or proptheta[k] + dt[k] > 1:
                    dt[k] = random.gauss(0,vartheta[k])

            proptheta = proptheta + dt
            
            Ltest = logLikelyhood(proptheta)

            if Ltest > L[-1]:
                theta.append(proptheta)
                L.append(Ltest)
                Lmax = Ltest
            else:
                u = random.random()
                #if False: 
                if math.log(u) < Ltest - L[-1] - 10: #and math.log(u) < Ltest - Lmax:
                    theta.append(proptheta)
                    L.append(Ltest)
                else:
                    theta.append(theta[-1][:])
                    proptheta = theta[-1][:]
                    L.append(L[-1]) #!!!!! With this we are introducing a wrong
                               #method, but ensuring more stability
                               #towards the maximum!!!!
            outfile.write(str(L[-1]))
            for k in range(4):
                outfile.write(' ' + str(theta[-1][k]))
            outfile.write('\n')
            #print L[-1], theta[-1][0], theta[-1][1], theta[-1][2], theta[-1][3]
    outfile.close()
    #print Lmax, theta[-1][0], theta[-1][1]
    return theta, L


def doMetropolis2(logLikelyhood):
    N = 1000
    theta = []
    L = []
    vartheta = [1,1,0.3,0.3]
    theta.append(np.array([1,2,0.1,0.05]))
    proptheta = theta[-1][:]
    L.append(logLikelyhood(proptheta))
    
    outfile = open("hiddenMCMC2.txt",'w')
    outfile.write("#Hidden Markov Chain Monte Carlo\n")
    outfile.write("# LogLikelyhood   x   y\n")
    outfile.write(str(L[-1]) + ' ' + str(theta[-1][0]) + ' ' + str(theta[-1][1]) + '\n')
    outpropsf = open("proposedHMM.txt",'w')
    outpropsf.write("# LogLikelyhood   x   y\n")

    for i in range(N):
        Lmax = -100000
        index = 0
        props = []
        for j in range(100):
            dt = np.zeros((4))
            for l in range(4):
                while dt[l] <= 0:
                    dt[l] = random.gauss(0,vartheta[l])
                    if l in [2,3]:
                        while dt[l] <= 0 or dt[l] >= 1:
                            dt[l] = random.gauss(0,vartheta[l])

            proptheta = theta[-1] + dt
            
            Ltest = logLikelyhood(proptheta)
        
            props.append([Ltest, proptheta[0], proptheta[1], proptheta[2], proptheta[3]])
            for l in range(len(props[-1])):
                outpropsf.write(str(props[-1][l])+' ')
            outpropsf.write("\n")
            if Lmax < Ltest:
                Lmax = Ltest
                index = j
        outpropsf.write("\n\n")
        theta.append(np.array([props[index][1],props[index][2],props[index][3],props[index][4]]))
        L.append(props[index][0])
        print(i)

        

        outfile.write(str(L[-1]))
        for k in range(2):
            outfile.write(' ' + str(theta[-1][k]))
        outfile.write('\n')
        #print L[-1], theta[-1][0], theta[-1][1], theta[-1][2], theta[-1][3]
    outfile.close()
    #print Lmax, theta[-1][0], theta[-1][1]
    return theta, L

    

    
if __name__=="__main__":
    #doMetropolis(logLikelyhood)
    doMetropolis2(likelihood)
    #doMetropolis2(logLikelyhood)
    print()
    print(("#"+str( logLikelyhood([-2,-1,0.1,0.05]))))
    print(("#"+str( likelihood([3,2,0.1,0.05]) )))
