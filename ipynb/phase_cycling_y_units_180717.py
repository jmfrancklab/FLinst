
# coding: utf-8

get_ipython().magic(u'load_ext pyspecdata.ipy')


# # Here, we are looking for a recipe that tells us how to get sensible units for the signal voltage when we are applying a phase cycle.
# 
# **Conclusion:** We learn that we just need to set the phase cycle axes to $[0,1)$ (*i.e.* units of "cycle"), and we will get out signal that has units of average voltage per phase cycle step.  Thus, the net noise is reduced by a factor of $\sqrt{N}$

t = r_[0:1:100j]
# should be able to do this with nddata -- can't
test = t.copy()
test[0:50] = sin(2*pi*test[0:50]/0.2)
test[50:] = 0
d = nddata(test,['t']).labels('t',t)
d


# notice how I use an axis label that runs over the interval $[0,1)$ -- this is important
# below, this results in the AVERAGE signal intensity, and a noise intensity reduces by a factor of $\sqrt{N}$

d *= nddata(ones(4,dtype=complex128),['repeat']).labels('repeat',r_[0:4]/4.)
fake_data = d.add_noise(0.2)
fake_data


# Zoom in on the noise

display(fake_data)
ylim(-0.3,0.3)


# Now apply the "phase cycle"/"signal averaging"

fake_data.ft('repeat')


# Zoom in on the noise

display(fake_data)
ylim(-0.3,0.3)


