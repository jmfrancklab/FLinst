from pyspecdata import *
def zeroth_order_ph(d, fl=None):
    r'''determine the covariance of the datapoints
    in complex plane, and use to phase the
    zeroth-order even if the data is both negative
    and positive'''
    eigenValues, eigenVectors = eig(cov(c_[
        d.data.real,
        d.data.imag].T
        ))
    mean_point = d.data.mean()
    mean_vec = r_[mean_point.real,mean_point.imag]
    # next 3 lines from stackexchange -- sort by
    # eigenvalue
    idx = eigenValues.argsort()[::-1]   
    eigenValues = eigenValues[idx]
    eigenVectors = eigenVectors[:,idx]
    # determine the phase angle from direction of the
    # largest principle axis plus the mean
    rotation_vector = eigenVectors[:,0] + mean_vec
    ph0 = arctan2(rotation_vector[1],rotation_vector[0])
    if fl:
        eigenVectors *= (eigenValues.reshape(-1,2)*ones((2,1)))/eigenValues.max()*abs(d.data).max()
        d_forplot = d.C
        fl.next('check covariance test')
        fl.plot(
                d_forplot.data.real,
                d_forplot.data.imag,
                '.',
                alpha=0.25,
                label='before'
                )
        d_forplot /= exp(1j*ph0)
        fl.plot(
                d_forplot.data.real,
                d_forplot.data.imag,
                '.',
                alpha=0.25,
                label='after'
                )
        fl.plot(0,0,'ko', alpha=0.5)
        fl.plot(mean_vec[0],mean_vec[1],'kx', label='mean', alpha=0.5)
        evec_forplot = eigenVectors + mean_vec.reshape((-1,1))*ones((1,2))
        fl.plot(evec_forplot[0,0],evec_forplot[1,0],'o', alpha=0.5,
                label='first evec')
        fl.plot(evec_forplot[0,1],evec_forplot[1,1],'o', alpha=0.5)
        fl.plot(rotation_vector[0],rotation_vector[1],'o', alpha=0.5,
                label='rotation vector')
        ax = gca()
        ax.set_aspect('equal', adjustable='box')
    return exp(1j*ph0)
def hermitian_function_test(s, down_from_max=0.5, shift_val=1.0):
    r"""determine the center of the echo"""
    # {{{ determine where the "peak" of the echo is,
    # and use it to determine the max
    # shift
    s = s.C # need to copy, since I'm manipulating the axis here,
    # and am assuming the axis of the source data is not manipulated
    data_for_peak = abs(s).mean_all_but(['t2'])
    max_val = data_for_peak.data.max()
    pairs = data_for_peak.contiguous(lambda x: abs(x) >
            max_val*down_from_max)
    longest_pair = diff(pairs).argmax()
    peak_location = pairs[longest_pair,:]
    peak_center = peak_location.mean()
    s.setaxis('t2',lambda x: x-peak_center)
    s.register_axis({'t2':0})
    max_shift = diff(peak_location).item()/2
    # }}}
    # {{{ construct test arrays for T2 decay and shift
    shift_t = nddata(r_[-1*shift_val:1*shift_val:1200j]*max_shift, 'shift')
    # }}}
    s_foropt = s.C
    # {{{ time shift and correct for T2 decay
    s_foropt.ft('t2')
    s_foropt *= exp(1j*2*pi*shift_t*
            s_foropt.fromaxis('t2'))
    s_foropt.ift('t2')
    # }}}
    # {{{ make sure there's and odd number of points
    # and set phase of center point to 0
    s_foropt = s_foropt['t2':(-max_shift,max_shift)]
    n_points = ndshape(s_foropt)['t2']
    if n_points % 2 == 0:
        s_foropt = s_foropt['t2',:-1]
        n_points -= 1
    center_point = s_foropt['t2',n_points//2+1]
    s_foropt /= center_point/abs(center_point)
    # }}}
    residual = abs(s_foropt - s_foropt['t2',::-1].runcopy(conj)).mean_all_but(['shift','R2'])
    # in the following, weight for the total signal recovered
    residual = residual / abs(center_point).mean_all_but(['shift','R2'])
    residual.reorder('shift')
    minpoint = residual.argmin()
    best_shift = minpoint['shift']
    return residual,best_shift+peak_center
