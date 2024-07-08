from pyspecdata import *
import matplotlib as mpl
from matplotlib.pylab import text
from matplotlib.tri import Triangulation, TriAnalyzer, UniformTriRefiner
from matplotlib.colors import ListedColormap

data = load(getDATADIR(exp_type='test_equip')+'contourcm.npz')
cm = ListedColormap(data['cm'],
        name='test')
font = {'family' : 'sans-serif',
        'sans-serif' : 'Times New Roman',
        'weight' : 'normal',
        'size'   : 30}
mpl.rc('font', **font)
rcParams['mathtext.fontset'] = 'cm'

filename = '190610_Katie_drift_test_oil_34dBm_iris'
presentation = True # only for presentation purposes -- for the purposes
#                     of viewing results, you want to see where your
#                     datapoints are, what the interpolation is doing,
#                     etc.
data = load(getDATADIR(exp_type='test_equip')+filename+'.npz')
f_axis = data[data.files[0]]
rx_axis = data[data.files[1]]
t_axis = data[data.files[2]]
stop_index = where(rx_axis==180)
print "shape of t_axis",shape(t_axis)
# DO NOT index multi-dimensional arrays using a single index -- it creates code that is very hard to read
# I believe this is till a problem in places below, and should be fixed.
# e.g. t_axis[j,:] NEVER t_axis[j] -- this way the reader can jump in and know what dimensionality the code is
figure(figsize=(15,5),
        facecolor=(1,1,1,0))
ax = axes(#frameon=False,
        facecolor=(1,1,1,0.5))
#ax.set_alpha(0.5)
for x in r_[0:len(f_axis)]:
    plot(t_axis[x,:len(t_axis[1])-1],rx_axis[x,:len(t_axis[1])-1]/10.,'o-',label='%0.7f GHz'%(f_axis[x]*1e-9))
fs = filename.split('_')
substance = [j.capitalize()
        for j in fs
        if j.lower() in ['air','oil']
        ]
assert len(substance) == 1
substance = substance[0]
power = [j[:-3]
        for j in fs
        if j[-3:].lower() == 'dbm'
        ]
assert len(power) == 1
power = power[0]
title(substance+' at '+power+' dBm')
xlabel('time (sec)')
ylabel('receiver (mV)')
grid();legend();
lg = legend(**dict(bbox_to_anchor=(1.05,1), loc=2, borderaxespad=0.))
lg.set_alpha(0.5)
savefig(filename+'.png',
        dpi=300,bbox_inches='tight',
        facecolor=(1,1,1,0),
        )
# {{{ generate the surface plot using fancy methods for a nice plot
# creates the Delauney meshing
tri_y = t_axis.ravel()
tri_x = ((f_axis[:,newaxis]*ones_like(t_axis)).ravel()
        -f_axis.mean())/1e3
tri_z = rx_axis.ravel()
# {{{ this part is actually very important, and prevents the data from
# interpolating to 0 at the edges!
# --> in the future, note that nan is a good placeholder for "lack of data"
mask = tri_y == 0 # t=0 are not valid datapoints
tri_y = tri_y[~mask]
tri_x = tri_x[~mask]
tri_z = tri_z[~mask]
# }}}
tri = Triangulation(tri_x,
        tri_y)
# {{{ refining the data -- see https://matplotlib.org/3.1.0/gallery/images_contours_and_fields/tricontour_smooth_delaunay.html#sphx-glr-gallery-images-contours-and-fields-tricontour-smooth-delaunay-py
#     I don't see a difference in the refined (tri_refi) vs. unrefined (tri),
#     but I'm quite possibly missing something, or it's more helpful in other cases
refiner = UniformTriRefiner(tri)
subdiv = 3  # Number of recursive subdivisions of the initial mesh for smooth
            # plots. Values >3 might result in a very high number of triangles
            # for the refine mesh: new triangles numbering = (4**subdiv)*ntri
tri_refi, tri_z_refi = refiner.refine_field(tri_z, subdiv=subdiv)
mask = TriAnalyzer(tri_refi).get_flat_tri_mask(10)
tri_refi = tri_refi.set_mask(~mask)
# }}}
figure(figsize=(5,15),
        facecolor=(1,1,1,0))
if not presentation:
    plot(tri_x,tri_y,'o',
            color='k',alpha=0.3)
    triplot(tri,
            color='k',alpha=0.3)
tricontourf(tri,tri_z,
        levels=linspace(tri_z.min(),tri_z.max(),100),
        #cmap=cm,
        )
colorbar()
xlabel('frequency\n($\\nu_{\\mu w}-%0.5f$ GHz)/ kHz'%(f_axis.mean()/1e9))
ylabel('time / s')
savefig(filename+'_contour.png',
        dpi=300,bbox_inches='tight',
        facecolor=(1,1,1,0),
        )
# }}}
show()
