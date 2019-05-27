#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Random Variate generator
# Class to create random numbers based on a given description

import random
import scipy.stats as stats

from astroML.density_estimation import EmpiricalDistribution as ed

class RandomVariateGenerator:
    """
    Base class for generators of random numbers.
    """
    def __init__(self):
        """
        Default constructor for random variate generator
        """
        pass

    def generate(self, nsamples=1):
        """
        Generate n samples from the specified distribution
        """
        pass


class UniformRandomVariate(RandomVariateGenerator):
    """
    Uniform random variate generator
    """
    def __init__(self, vmin, vmax):
        """
        Create a new uniform random variate
        passing min and max values
        """
        self.min = vmin
        self.max = vmax
    
    def generate(self, nsamples=1):
        """
        Generate n samples using uniform distribution
        """
        return [
            random.uniform(self.min, self.max)
            for _ in range(nsamples)
        ]

class TheoreticalDistribution(RandomVariateGenerator):
    """
    Create a random variate generator based on a distrubution
    name and parameters
    """
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def generate(self, nsamples=1):
        """
        Generate n samples from theoretical distributions
        """
        # Obtain the random variate object
        dist = getattr(stats, self.name)
        # Generate the random variate
        return dist.rvs(* self.params, size=nsamples)

class EmpiricalDistribution(RandomVariateGenerator):
    """
    Depending of data variability, it is too hard to fit
    a theoretical distribution to the data. Therefore, an 
    empirical distribution can be used to mimic the originial
    distribution.
    """
    def __init__(self, data):
        self.data = data
        self.ecdf = ed(data)
    
    def generate(self, nsamples=1):
        """
        Generate data that mimics the originial data probability
        distribution.
        """
        return self.ecdf.rvs(nsamples)
