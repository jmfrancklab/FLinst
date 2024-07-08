
# coding: utf-8

# In[1]:

get_ipython().magic(u'load_ext pyspecdata.ipy')
from pyspecdata.fornotebook import standard_noise_comparison, save_data
init_logging(level=logging.DEBUG)
logger.debug("a test!")


# # Current Summary
# 
# I should be able to run the cell that defines ``plot_noise``. In trying to get it to work, I realized that I needed to replace `load_file` (old style) with `find_file`.
# Because the data was in a subdirectory of a subdirectory of the reference data, there was trouble finding it.
# I needed to tweak pyspecdata's file-finding routines, so you need to be using version of pyspecdata that includes the changes in commit ba5d707342fb (just be sure you pull pyspecdata).
# 
# *Note that the calibration argument got dropped in the update -- this is just fine -- we should probably do the calibration explicitly, anyways.*

# When I'm done, I should pull all these functions out of pyspecdata, since they are applications.

# # Code
# pull the following from my notebooks

# In[ ]:

name = 'dna_cs14_120314'
standard_noise_comparison(name)


# since this calls on plot_noise (which was deleted when nmr.py was deleted), go back to git and retrieve the plot_noise function

# In[2]:

#{{{ plot_noise
def plot_noise(filename, expno, calibration, mask_start, mask_stop,
        rgmin=0, smoothing=False, both=False, T=293.0,
        plottype='semilogy', retplot=False, exp_type='shared_drive'):
    '''plot noise scan as resistance'''
    data = find_file(filename, expno=expno,
            exp_type=exp_type)
    data *= calibration
    data.ft('t2',shift = True)
    newt2 = r'F2 / $Hz$'
    data.rename('t2',newt2)
    v = data.get_prop('acq')
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
            plotdata.ift(newt2)
            t = plotdata.getaxis(newt2).copy()
            t[:] = originalt
            # end convolution
            pval = plot(plotdata,'-',alpha=0.5,plottype = plottype)
            retval += ['%d: '%j+data.get_prop('title')+' $t_{dwov}$ %0.1f RG %d, DE %0.2f, mean %0.1f'%(dwov*1e6,rg,de,avg)]
            axis('tight')
        if retplot:
            return pval,retval
        else:
            return retval
    else:
        return []
#}}}


# also, just retrieve the standard_noise_comparison function, since I will probably want to edit it

# In[ ]:

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


# Here, I want to pull out the potion of ``standard_noise_comparison`` that plots the reference scans

# In[4]:

figure(1,figsize=(16,8))
#data_subdir = 'shared_drive' # call with this once, so it finds the reference_data directory
#{{{ pull the cnsi calibration info from the data text file
v = save_data()
our_calibration = double(v['our_calibration'])
cnsi_calibration = double(v['cnsi_calibration'])
calibration = cnsi_calibration*sqrt(50.0/10.0)*sqrt(50.0/40.0)
#}}}
name_list = []
dir_list = []
explabel = []
noiseexpno = []
signalexpno = []
plotlabel = 'example_noise'
#
name_list += ['popem_4mM_5p_pct_110610']
dir_list += ['reference_data']
explabel += ['control without shield']
noiseexpno += [3] # 3 is the noise scan 2 is the reference
#
name_list += ['dna_cs14_120314']
dir_list += ['franck_cnsi']
explabel += ['with shield']
noiseexpno += [3] # 3 is the noise scan 2 is the reference
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
      retval = plot_noise(name_list[k], noiseexpno[k], calibration, mask_start,
              mask_stop, smoothing=smoothing,  both=False, retplot=True,
              exp_type=dir_list[k])
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
   if (ind % 2) ==  0:
      print '\n\n'


# here is a show command for when we're running from the command line

# In[ ]:

show()

