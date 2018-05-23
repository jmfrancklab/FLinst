
# coding: utf-8

# In[1]:

get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata.fornotebook import standard_noise_comparison, save_data


# In[ ]:

# pull the following from my notebooks

name = 'dna_cs14_120314'
standard_noise_comparison(name)


# In[ ]:

# since this calls on plot_noise (which was deleted when nmr.py was deleted), go back to git and retrieve the plot_noise function


# In[ ]:

#{{{ plot_noise
def plot_noise(path,j,calibration,mask_start,mask_stop,rgmin=0,k_B = None,smoothing = False, both = False, T = 293.0,plottype = 'semilogy',retplot = False):
    '''plot noise scan as resistance'''
    filename = r'%s%d'%(path,j)
    try:
        data = load_file(filename,calibration=calibration)
    except:
        raise CustomError('error loading file'+filename)
    k_B = 1.3806504e-23
    data.ft('t2',shift = True)
    newt2 = r'F2 / $Hz$'
    data.rename('t2',newt2)
    v = bruker.load_acqu(r'%s%d/'%(path,j))
    dw = 1/v['SW_h']
    dwov = dw/v['DECIM']
    rg = v['RG']
    de = v['DE']
    aq = v['TD']*dw
    if rg>rgmin:
        plotdata = abs(data)
        plotdata.data **= 2
        johnson_factor = 4.0*k_B*T
        plotdata.data /= (aq*johnson_factor)
        t = data.getaxis(newt2)
        mask = logical_and(t>mask_start,
            t<mask_stop)
        try:
            avg = plotdata.data[mask].mean() 
        except IndexError:
            raise CustomError('error trying to mask for the average because the mask is',mask,'of shape',shape(mask),'for shape(plotdata)=',shape(plotdata.data))
        retval = []
        if both or not smoothing:
            pval = plot(plotdata,'-',alpha=0.5,plottype = plottype)
            retval += ['%d: '%j+bruker.load_title(r'%s%d'%(path,j))+'$t_{dw}$ %0.1f $t_{dwov}$ %0.1f RG %d, DE %0.2f, mean %0.1f'%(dw*1e6,dwov*1e6,rg,de,avg)]
            axis('tight')
        if smoothing:
            # begin convolution
            originalt = plotdata.getaxis(newt2).copy()
            plotdata.ft(newt2,shift = True)
            sigma = smoothing
            siginv = 0.5*sigma**2 # here, sigma is given in the original units (i.e. what we're convolving)
            t = plotdata.getaxis(newt2)
            g = exp(-siginv*t.copy()**2) # we use unnormalized kernel (1 at 0), which is not what I thought!
            plotdata.data *= g
            plotdata.ift(newt2,shift = True)
            t = plotdata.getaxis(newt2).copy()
            t[:] = originalt
            # end convolution
            pval = plot(plotdata,'-',alpha=0.5,plottype = plottype)
            retval += ['%d: '%j+bruker.load_title(r'%s%d'%(path,j))+' $t_{dwov}$ %0.1f RG %d, DE %0.2f, mean %0.1f'%(dwov*1e6,rg,de,avg)]
            axis('tight')
        if retplot:
            return pval,retval
        else:
            return retval
    else:
        return []
#}}}


# In[2]:

# also, just retrieve the standard_noise_comparison function, since I will probably want to edit it

def standard_noise_comparison(name,path = 'franck_cnsi/nmr/', data_subdir = 'reference_data',expnos = [3]):
    print '\n\n'
    # noise tests
    close(1)
    figure(1,figsize=(16,8))
    v = save_data();our_calibration = double(v['our_calibration']);cnsi_calibration = double(v['cnsi_calibration'])
    calibration = cnsi_calibration*sqrt(50.0/10.0)*sqrt(50.0/40.0)
    path_list = []
    explabel = []
    noiseexpno = []
    signalexpno = []
    plotlabel = name+'_noise'
    #
    path_list += [getDATADIR()+'%s/nmr/popem_4mM_5p_pct_110610/'%data_subdir]
    explabel += ['control without shield']
    noiseexpno += [3] # 3 is the noise scan 2 is the reference
    path_list += [getDATADIR()+'%s/nmr/noisetest100916/'%data_subdir] + [getDATADIR()+path+name+'/']*len(expnos)
    explabel += ['']+[r'$\mathbf{this experiment}$']*len(expnos)
    noiseexpno += [2]+expnos # 3 is the noise scan 2 is the reference
    #
    mask_start = -1e6
    mask_stop = 1e6
    ind = 0
    smoothing = 5e3
    for j in range(0,1): # for multiple plots $\Rightarrow$ add in j index below if this is what i want
       figure(1)
       ind += 1
       legendstr = []
       linelist = []
       subplot(121) # so that legend will fit
       for k in range(0,len(noiseexpno)):
          retval = plot_noise(path_list[k],noiseexpno[k],calibration,mask_start,mask_stop,smoothing = smoothing, both = False,retplot = True)
          linelist += retval[0]
          legendstr.append('\n'.join(textwrap.wrap(explabel[k]+':'+retval[1][0],50))+'\n')
       ylabel(r'$\Omega$')
       titlestr = 'Noise scans (smoothed %0.2f $kHz$) for CNSI spectrometer\n'%(smoothing/1e3)
       title(titlestr+r'$n V$ RG/ disk units = %0.3f, mask (%0.3f,%0.3f)'%(calibration*1e9,mask_start,mask_stop))
       ax = gca()
       ylims = list(ax.get_ylim())
       #gridandtick(gca(),formatonly = True)
       gridandtick(gca(),logarithmic = True)
       subplot(122)
       grid(False)
       lg = autolegend(linelist,legendstr)
       ax = gca()
       ax.get_xaxis().set_visible(False)
       ax.get_yaxis().set_visible(False)
       map((lambda x: x.set_visible(False)),ax.spines.values())
       lplot('noise'+plotlabel+'_%d.pdf'%ind,grid=False,width=5,gensvg=True)
       print '\n\n'
       figure(2)
       legendstr = []
       for k in range(0,len(signalexpno)):
          data = load_file(dirformat(path_list[k])+'%d'%noiseexpno[k],calibration=calibration)
          data.ft('t2',shift = True)
          x = data.getaxis('t2')
          data['t2',abs(x)>1e3] = 0
          data.ift('t2',shift = True)
          plot(abs(data['t2',0:300])*1e9)
          xlabel('signal / $nV$')
          legendstr += [explabel[k]]
       if len(signalexpno)>0:
           autolegend(legendstr)
           lplot('signal'+plotlabel+'_%d.pdf'%ind,grid=False)
       if (ind % 2) ==  0:
          print '\n\n'


# In[ ]:

get_ipython().magic(u'pinfo save_data')


# In[ ]:



