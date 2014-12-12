import numpy as np
import pysm.new_cython
import readImage
import filters
import markPosition
import sys
import convertFiles
from scipy import ndimage, optimize


def writeDetectedParticles(particles,frame,outfile):
    outfile.write('\n#-Frame {:2.0f} -------------------------------------\n'.format(frame))
    outfile.write('#-Number-of-particles: ' + str(len(particles[0])) + '\n')
    outfile.write('#-Cutoff-value-used: {:} \n'.format(particles[1]))
    outfile.write("# x       y        width_x      width_y   height  amplitude  sn  volume \n")
    for p in particles[0]:
        outfile.write('{:} {:} {:} {:} {:} {:} {:} {:} \n'.format(p.x,p.y,p.width_x,p.width_y,p.height,p.amplitude,p.sn,p.volume))
    return

def outMarkedImages(image,partdata,out):

    markNoInit = markPosition.markPositionsFromList(image.shape,partdata[0])
    markFromNoInit = markPosition.markPositionsSimpleList(image.shape,readLocalMax("foundLocalMaxima.txt"))
    boxMarkings = markPosition.drawBox(image.shape,readBox("localBoxes.txt"))
    
    '''
    ofile = open("simNoInit.txt",'w')
    writeDetectedParticles(partdata,1,ofile)
    '''

    outar = markPosition.autoScale(markPosition.convertRGBGrey(image))
    #outar = markPosition.imposeWithColor(outar,markInit,'B')
    #outar = markPosition.imposeWithColor(outar,markFromNoInit,'G')
    outar = markPosition.imposeWithColor(outar,markNoInit,'R')
    outar = markPosition.imposeWithColor(outar,boxMarkings,'G')

    markPosition.saveRGBImage(outar,out)
    return

def multiImageDetect(img,
                    sigma,
                    local_max_window,
                    signal_power,
                    bit_depth,
                    eccentricity_thresh,
                    sigma_thresh,numAdder,local_max=None,output=False):
    particle_data = []
    frame = 0
    outfile = open("foundParticles.txt",'w')
    if not (local_max is None):
        local_max_pixels = convertFiles.giveLocalMaxValues(convertFiles.convImageJTrack(local_max),len(img))
        
    count = 0
    print('_' * 52)
    sys.stdout.write("[")
    sys.stdout.flush()
    for i in xrange(len(img)):

        #Read image
        image = readImage.readImage(img[i])

        frame += 1
        #TODO: computationally better adding up of frames
        '''
        #Good: (but not working) Adding up images
        if frame == 1:
            a = np.zeros(image.shape)
        a += image

        if frame > numAdder:
            #remove last image
            b = readImage.readImage(img[i-numAdder])
            a -= b
            ch = a != (image + readImage.readImage(img[i-1]) + readImage.readImage(img[i-2]))
            if ch.all():
                sys.exit("Oh man, what's going on in frame {:}?".format(frame))
                    
        else:
            continue
        '''
        #Computationally expensive Adding up images
        if frame < numAdder:
            continue
        else:
            a = np.zeros(image.shape)
            for j in xrange(numAdder):
                a += readImage.readImage(img[i-j])

        if output:
            readImage.saveImageToFile(a,"01sanityCheck{:0004d}.png".format(frame))

        #print("\n==== Doing image no " + str(frame) + " ====")
        if local_max is None:
            particles = detectParticles(
                    a,
                    sigma,
                    local_max_window,
                    signal_power,
                    bit_depth,
                    frame,
                    eccentricity_thresh,
                    sigma_thresh,
                    output=output)
        else:
            particles = detectParticles(
                    a,
                    sigma,
                    local_max_window,
                    signal_power,
                    bit_depth,
                    frame,
                    eccentricity_thresh,
                    sigma_thresh,
                    local_max_pixels=local_max_pixels[i],
                    output=output)

        outMarkedImages(a,particles,"out{:0004d}.tif".format(frame))
        a = np.zeros(image.shape)
        particle_data.append(particles)
        writeDetectedParticles(particles,frame,outfile)
        aaa = int(i * 50/len(img))
        if aaa > count:
            sys.stdout.write("#"*(aaa-count))
            sys.stdout.flush()
            count += aaa-count
    outfile.close()
    sys.stdout.write("#"*(50-aaa)+"]\n")
    pd = []
    for fr in particle_data:
        pd.append(fr[0])
#    print pd
    return pd



def fitgaussian2d(data, background_mean, user_moments = None):
    """Returns (height, amplitude, x, y, width_x, width_y) as a numpy array
    found by least squares fitting of gaussian variables:"""
    
    if user_moments == None:
        initial_params = image_moments(data, background_mean)
    else:
        initial_params = user_moments
    
    #ravel is a special case for "unraveling" higher dimensional arrays into 1D arrays
    errorfunction = lambda p: np.ravel((gaussian2d(*p)(*np.indices(data.shape)) - data))
    p, cov, infodict, errmsg, success = optimize.leastsq(errorfunction, initial_params, full_output=1)
    return p



def image_moments(data, mean_background):
    total = data.sum()
    Y,X = np.indices(data.shape)
  
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    
    col = data[:, int(x)]
    width_y = np.sqrt(np.abs((np.arange(col.size)-y)**2*col).sum()/col.sum())
    
    row = data[int(y), :]
    width_x = np.sqrt(np.abs((np.arange(row.size)-x)**2*row).sum()/row.sum())
    
    height = mean_background
    amplitude = data.max() - height
    
    return (height, amplitude, x, y, width_x, width_y)



def gaussian2d(height, amplitude, center_x, 
               center_y, width_x, width_y):
    """Return 2d gaussian lamda(x,y) function"""
    
    height = float(height)
    amplitude = float(amplitude)
    width_x = float(width_x)
    width_y = float(width_y)
    
    return (lambda x,y: height + 
            amplitude*np.exp(-(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2))



def filterImage(image,sigma,local_max_window,signal_power,output):
    median_img = ndimage.filters.median_filter(image, (21,21))
    if False:
        readImage.saveImageToFile(median_img,"05MedianFilter1.png")
    (background_mean,background_std) = (median_img.mean(),median_img.std())
    print background_mean, background_std
    #cutoff = readImage.otsuMethod(image)
    cutoff = background_mean + signal_power * background_std
    print cutoff

    boxcarImage = filters.boxcarFilter(image,boxsize=5,cutoff=cutoff)
    if output:
        readImage.saveImageToFile(boxcarImage,"02boxFilter.png")

    gausFiltImage = ndimage.filters.gaussian_filter(boxcarImage,sigma,order=0)
    if output:
        readImage.saveImageToFile(gausFiltImage,"02gaussFilter.png")
    
    localMaxImage = ndimage.filters.maximum_filter(gausFiltImage,size=local_max_window)
    if output:
        readImage.saveImageToFile(localMaxImage,"03localMax.png")

    img_max_filter = gausFiltImage.copy()
    img_max_filter[(gausFiltImage != localMaxImage)] = 0
    if output:
        readImage.saveImageToFile(img_max_filter,"04MaxFilter.png")
    
#    print("Cutoff is at: {:}".format(cutoff))
    median_img = ndimage.filters.median_filter(gausFiltImage, (21,21))
    if False:
        readImage.saveImageToFile(median_img,"05MedianFilter2.png")
    background_mean = median_img.mean()
    #cutoff = readImage.otsuMethod(image)
            #background_std) = (median_img.mean(),median_img.std())
    #cutoff = readImage.otsuMethod(image)
    cutoff = background_mean + signal_power * background_std
    print background_mean, background_std
    print cutoff

    print("Cutoff is at: {:}".format(cutoff))
    print("Max of MaxFilter is at: {:}".format(img_max_filter.max()))
    imgMaxNoBack = (img_max_filter >= cutoff)
    if output:
        readImage.saveImageToFile(imgMaxNoBack,"05MaxBinary.png")
     #Check if maxima found
    if imgMaxNoBack.any() == False:
        print("Error: No max pixels detected.")

    local_max_pixels = np.nonzero(imgMaxNoBack)
    
    print('Cutoff is at ' + str(cutoff))
    print("Found local Maxima: "+str(len(local_max_pixels[0])))


    return (local_max_pixels,cutoff,background_mean)

def readLocalMax(inf):
    local_max = []
    infile = open(inf,'r')
    for line in infile:
        (a,x,y) = line.split()
        local_max.append([0,int(x),int(y)])
    infile.close()
    return local_max


def setFittingROI(imageshape,lmpx,lmpy,boxsize=7):

    num_rows = imageshape[0]
    num_cols = imageshape[1]

    #print np.transpose(local_max_pixels)
    row0 = int(lmpx)
    col0 = int(lmpy)
    #print(row0,' ',col0)

    row_min = row0 - boxsize/2
    row_max = row0 + boxsize/2
    col_min = col0 - boxsize/2
    col_max = col0 + boxsize/2

    if (row_min < 0 or row_max >= num_rows or
            col_min < 0 or col_max >= num_cols):
        #print("Oh, too close to frame boarder to fit a gaussian.")
        return False
    else:
        return (row_min,row_max,col_min,col_max)
        



def determineFittingROI(imageshape,lmpx,lmpy,signal_power,sigma):
    #TODO: Played around with signal_power:
    template_size = signal_power * np.ceil(sigma) - 1
    #template_size = 10 * np.ceil(sigma) - 1

    psf_range = np.floor(template_size/2)

    num_rows = imageshape[0]
    num_cols = imageshape[1]

    #print np.transpose(local_max_pixels)
    row0 = int(lmpx)
    col0 = int(lmpy)
    #print(row0,' ',col0)

    row_min = row0 - psf_range
    row_max = row0 + psf_range
    col_min = col0 - psf_range
    col_max = col0 + psf_range

    if (row_min < 0 or row_max >= num_rows or
            col_min < 0 or col_max >= num_cols):
        #print("Oh, too close to frame boarder to fit a gaussian.")
        return False
    else:
        #print("So where is the point?")
        return (row_min,row_max,col_min,col_max)



def checkFit(fitdata,sigma,sigma_thresh,eccentricity_thresh,nunocon,nunoexc,nusigma):
    ##############
    #FIT CHECKING
    ##############
    if fitdata[0] <= 0 or fitdata[1] <=0:
        #print("Fit did not converge")
        #Fit did not converge
        nunocon += 1
        return False, nunocon,nunoexc,nusigma

    if (np.abs(fitdata[5]/fitdata[4]) >= eccentricity_thresh or 
        np.abs(fitdata[4]/fitdata[5]) >= eccentricity_thresh):
        
        #print("Fit too eccentric")
        #Fit too eccentric
        nunoexc += 1
        return False, nunocon,nunoexc,nusigma

    '''
    if (fitdata[4] > (sigma_thresh * sigma) or 
        fitdata[4] < (sigma / sigma_thresh) or
        fitdata[5] > (sigma_thresh * sigma) or
        fitdata[5] < (sigma / sigma_thresh)):
        print("Fit too unlike theoretical psf")
        if fitdata[4] > (sigma_thresh * sigma) :
            print("spot x too large")
        elif fitdata[4] < (sigma / sigma_thresh):
            print("spot x too small")
        elif fitdata[5] > (sigma_thresh * sigma):
            print("spot y too large")
        elif fitdata[5] < (sigma / sigma_thresh):   
            print("spot y too small")
        #Fit too unlike theoretical psf
        nusigma += 1
        return False, nunocon,nunoexc,nusigma
    '''
    if ((fitdata[4]**2+fitdata[5]**2) > (sigma_thresh * sigma)**2 or 
        (fitdata[4]**2+fitdata[5]**2) < (sigma / sigma_thresh)**2):
        #print("Fit too unlike theoretical psf")
        #Fit too unlike theoretical psf
        nusigma += 1
        return False, nunocon,nunoexc,nusigma

    return True,nunocon,nunoexc,nusigma
    


def addParticleToList(particle_list,frame,row_min,row_max,col_min,col_max,fitdata):
        #Create a new Particle
        #TODO:        
        #p = cparticle.CParticle()
        p = pysm.new_cython.TempParticle()        
        
        #TODO: Implement Particle ID
        p.frame = frame
        p.position = np.array([row_min, row_max, col_min, col_max])
        
        p.height = fitdata[0]
        p.amplitude = fitdata[1]
        
        #TODO: FIX THIS BUG (switching of x and y)
        p.y = fitdata[2] + row_min + 1
        p.x = fitdata[3] + col_min + 1
        p.width_x = np.abs(fitdata[4])
        p.width_y = np.abs(fitdata[5])
        p.volume = (2 * np.pi * p.amplitude * p.width_x * p.width_y)
        
        # normalized volume for intensity moment descrimination in
        # linking step
        p.norm_volume = (2 * np.pi * p.amplitude * p.width_x * p.width_y)
        
        # calculate signal to noise
        # (for our purposes a simple calc of amplitude of signal minus 
        # the background over the intensity of the background)
        p.sn = (p.amplitude + p.height) / p.height
        particle_list.append(p)
        return



def findParticleAndAdd(image,frame,local_max_pixels,signal_power,sigma,background_mean,sigma_thresh,eccentricity_thresh,bit_depth):
    
    particle_list = []

    nunocon = 0
    nunoexc = 0
    nusigma = 0
    nupart = 0
    nuedge = 0

    outf = open("localBoxes.txt",'w')
    for i in xrange(len(local_max_pixels[0])):
        
        #isIt = determineFittingROI(image.shape,local_max_pixels[0][i],local_max_pixels[1][i],signal_power,sigma)
        isIt = setFittingROI(image.shape,local_max_pixels[0][i],local_max_pixels[1][i],7)
        if isIt:
            row_min,row_max,col_min,col_max = isIt
        else:
            #print "ohoh"
            nuedge += 1
            continue
        outf.write("{:} {:} {:} {:}\n".format(row_min,row_max,col_min,col_max))

        fitdata = fitgaussian2d(
                    image[row_min:row_max+1, col_min:col_max+1],
                    background_mean)

        checkedfit = checkFit(fitdata,sigma,sigma_thresh,eccentricity_thresh,nunocon,nunoexc,nusigma)
        if not checkedfit[0]:
            nunocon,nunoexc,nusigma = checkedfit[1:]
            continue

        addParticleToList(particle_list,frame,row_min,row_max,col_min,col_max,fitdata)
        nupart += 1
    outf.close()
    return particle_list,nupart,nunocon,nunoexc,nusigma,nuedge


def readBox(inf):
    infile = open(inf,'r')
    boxList = []
    for line in infile:
        (xmin,xmax,ymin,ymax) = line.split()
        boxList.append([float(xmin),float(xmax),float(ymin),float(ymax)])
    infile.close
    return boxList



def detectParticles(img,sigma,local_max_window,signal_power,bit_depth,frame,eccentricity_thresh,sigma_thresh,local_max_pixels=None,output=False):

    #Check if initial positions are given
    if (local_max_pixels is None):
        #Filter Image and get initial particle positions
        local_max_pixels,cutoff,background_mean = filterImage(img,sigma,local_max_window,signal_power,output)
    else:
        cutoff = 0

    outf = open("foundLocalMaxima.txt",'w')
    for i in xrange(len(local_max_pixels[0])):
        outf.write("1 {:} {:}\n".format(local_max_pixels[0][i],local_max_pixels[1][i]))
    outf.close()

    # Get Background and STD (has to be redone)
    median_img = ndimage.filters.median_filter(img, (21,21))
    (background_mean,background_std) = (median_img.mean(),median_img.std())

    #Fit Gauss to Image and add to Particle list if ok
    particle_list,nupart,nunocon,nunoexc,nusigma,nuedge = findParticleAndAdd(img,frame,local_max_pixels,signal_power,sigma,background_mean,sigma_thresh,eccentricity_thresh,bit_depth)

    #Check, that all possible positions were considered.
    sumparts = nunocon+nunoexc+nusigma+int(nuedge)+nupart
    if sumparts != len(local_max_pixels[0]):
        print("Not converged:  {:5d}".format(nunocon))
        print("Too excentric:  {:5d}".format(nunoexc))
        print("Wrong Sigma:    {:5d}".format(nusigma))
        print("close to Edge:  {:5d}".format(int(nuedge)))
        print("Appended Parts: {:5d}".format(nupart))
        print("                +++++") 
        print("Sum:            {:5d}".format(sumparts))
        raise Exception("Error: number of maxPixels not equal to processed positions\n")
    #print("Number of Particles found: " + str(len(particle_list)))

    return [particle_list,cutoff]

