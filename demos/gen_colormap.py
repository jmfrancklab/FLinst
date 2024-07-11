from pyspecdata import *
from skimage import color as skc
from matplotlib.colors import ListedColormap
#{{{ constructing and saving the colormap
colors = array([[1,1,1],
    [0.25,0.25,0.25],
    [0,1,1],
    [1,1,0],
    [1,0,0],
    ],
    dtype=float)
#rgb2lab expects an image, so a 3D object
colors_lab = skc.rgb2lab(colors[newaxis,:,:])[0,:,:]
colors[4,0] = colors[3,0] # match the L of red to orange
orig_x = r_[0:len(colors)]
new_x = r_[0:len(colors)-1:256j]
newcolor = zeros((256,3),dtype=float)
for j in range(3):
    f = interp1d(orig_x,colors_lab[:,j])
    newcolor[:,j] = f(new_x)
newcolor = skc.lab2rgb(newcolor[newaxis,:,:])[0,:,:]
savez(getDATADIR(exp_type='test_equip')+'contourcm.npz',cm=newcolor)
#}}}
# {{{ use this command to load the colormap
data = load(getDATADIR(exp_type='test_equip')+'contourcm.npz')
cm = ListedColormap(data['cm'],
        name='test')
# }}}
