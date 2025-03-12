import os
import time
from log_psplines.psplines import LogPSplines
from log_psplines.datasets import Timeseries, Periodogram
from log_psplines.mcmc import run_mcmc
from log_psplines.plotting import plot_pdgrm
import matplotlib.pyplot as plt
import numpy as np
import jax.numpy as jnp
import scipy
from tqdm.auto import tqdm

import os

outdir = 'plots'
os.makedirs(outdir, exist_ok=True)

a_coeff = [1, -2.2137, 2.9403, -2.1697, 0.9606]
n_samples = 1024
fs = 100  # Sampling frequency in Hz.
dt = 1.0 / fs
t = jnp.array(np.linspace(0, (n_samples - 1) * dt, n_samples))
noise = scipy.signal.lfilter([1], a_coeff, np.random.randn(n_samples))
noise = jnp.array((noise - np.mean(noise)) / np.std(noise))
mock_pdgrm = Timeseries(t, noise).to_periodogram().highpass(5)

kwgs = dict(
    pdgrm=mock_pdgrm, num_samples=50, num_warmup=50, verbose=False
)

runtimes = []
ks = np.geomspace(8, 100, num=10, dtype=int)
reps = 3
for k in tqdm(ks):
    print(f"Running all reps for k: {k}\n")
    spline_model, samples = None, None
    for rep in range(reps):
        t0 = time.time()
        samples, spline_model = run_mcmc(n_knots=k, **kwgs)
        runtime = float(time.time()) - t0
        runtimes.append(runtime)

    fig, ax = plot_pdgrm(mock_pdgrm, spline_model, samples['weights'])
    fig.savefig(os.path.join(outdir, f"test_mcmc_{k}.png"))
    plt.close(fig)

# save  [k , runtime]
median_runtimes = np.median(np.array(runtimes).reshape(len(ks), reps), axis=1)
std_runtimes = np.std(np.array(runtimes).reshape(len(ks), reps), axis=1)
np.save(os.path.join(outdir, "mcmc_runtimes.npy"), np.array([ks, median_runtimes, std_runtimes]))

plt.figure()
plt.fill_between(ks, median_runtimes - std_runtimes, median_runtimes + std_runtimes, color='tab:orange')
plt.xlabel("Number of knots")
plt.ylabel("Runtime (s)")
plt.xscale('log')
plt.savefig(os.path.join(outdir, "mcmc_runtimes.png"))