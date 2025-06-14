import time
from typing import Tuple

import jax
import jax.numpy as jnp
from numpyro.infer import MCMC, NUTS
from numpyro.infer.util import init_to_value

from .bayesian_model import bayesian_model
from .datatypes import Periodogram
from .psplines import LogPSplines


def run_mcmc(
    pdgrm: Periodogram,
    parametric_model: jnp.ndarray = None,
    alpha_phi=1.0,
    beta_phi=1.0,
    alpha_delta=1e-4,
    beta_delta=1e-4,
    num_warmup=500,
    num_samples=1000,
    rng_key=0,
    verbose=True,
    **spline_kwgs,
) -> Tuple[MCMC, LogPSplines]:
    # Initialize the model + starting values
    rng_key = jax.random.PRNGKey(rng_key)
    log_pdgrm = jnp.log(pdgrm.power)
    spline_model = LogPSplines.from_periodogram(
        pdgrm,
        n_knots=spline_kwgs.get("n_knots", 10),
        degree=spline_kwgs.get("degree", 3),
        diffMatrixOrder=spline_kwgs.get("diffMatrixOrder", 2),
        parametric_model=parametric_model,
    )
    print("Spline model:", spline_model)
    delta_0 = alpha_delta / beta_delta
    phi_0 = alpha_phi / (beta_phi * delta_0)
    init_strategy = init_to_value(
        values=dict(delta=delta_0, phi=phi_0, weights=spline_model.weights)
    )

    # Setup and run MCMC using NUTS
    kernel = NUTS(bayesian_model, init_strategy=init_strategy)
    mcmc = MCMC(
        kernel,
        num_warmup=num_warmup,
        num_samples=num_samples,
        progress_bar=verbose,
        jit_model_args=True,
    )
    t0 = time.time()
    mcmc.run(
        rng_key,
        log_pdgrm,
        spline_model.basis,
        spline_model.penalty_matrix,
        spline_model.log_parametric_model,
        alpha_phi,
        beta_phi,
        alpha_delta,
        beta_delta,
    )
    # add attribute to the MCMC object for the spline model
    setattr(mcmc, "runtime", time.time() - t0)

    return mcmc, spline_model
