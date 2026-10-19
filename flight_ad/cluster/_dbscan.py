import numpy as np
from sklearn.cluster import DBSCAN as sklearn_dbscan
from sklearn.neighbors import NearestNeighbors
from flight_ad.math.geometry import curvature

__all__ = ['DBSCAN', 'calculate_eps']


def calculate_eps(X, mode=None, **kwargs):
    """Calculate epsilon hyperparameter for DBSCAN using curvature analysis.

    Sorts k-nearest-neighbour distances and returns the distance at the
    point of maximum curvature (the "elbow"), which separates the dense
    core region from noise without requiring manual tuning.

    Parameters
    ----------
    X : array-like of shape (n_samples, n_features)
    mode : callable or None
        If None, uses the empirical elbow on raw distances.
        If a callable (e.g. numpy.polyfit), fits a polynomial first.
        Pass ``degree`` as a keyword argument when using a fitting function.

    Returns
    -------
    y_max_curvature : float
    x : ndarray
    y : ndarray
    """
    if mode is None:
        fun = None
        mode = 'empirical'
    else:
        fun = mode
        mode = 'user-defined'

    neighbors = NearestNeighbors(n_neighbors=2)
    neighbors.fit(X)
    distances, _ = neighbors.kneighbors(X)
    distances = np.sort(distances, axis=0)[:, 1]

    if mode == 'empirical':
        x = np.arange(len(distances))
        y = distances
        y_max_curvature = y[np.argmax(curvature(x, y))]
    else:
        x0 = np.arange(len(distances))
        y0 = distances
        poly = fun(x0, y0, kwargs['degree'])
        x = np.linspace(0, len(distances), 1000)
        y = np.polyval(poly, x)
        y_max_curvature = y[np.argmax(curvature(x, y))]
    return y_max_curvature, x, y


class DBSCAN(sklearn_dbscan):
    """DBSCAN with automatic epsilon (eps) selection.

    Extends sklearn.cluster.DBSCAN by computing the optimal ``eps`` from
    the data when ``eps=None`` (the default).  The elbow of the sorted
    k-nearest-neighbour distance curve is used as the neighbourhood
    radius, eliminating manual hyperparameter tuning.

    Parameters
    ----------
    eps : float or None, default=None
        Neighbourhood radius.  Computed automatically when None.
    min_samples : int, default=5
    metric : str or callable, default='euclidean'
    metric_params : dict or None, default=None
    algorithm : str, default='auto'
    leaf_size : int, default=30
    p : float or None, default=None
    n_jobs : int or None, default=None
    """

    def __init__(self, eps=None, *, min_samples=5, metric='euclidean',
                 metric_params=None, algorithm='auto', leaf_size=30, p=None,
                 n_jobs=None):
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
        self.metric_params = metric_params
        self.algorithm = algorithm
        self.leaf_size = leaf_size
        self.p = p
        self.n_jobs = n_jobs

    def _resolve_eps(self, X):
        """Compute eps from data if not yet set, then sync state to sklearn parent."""
        if self.eps is None:
            self.eps, _, _ = calculate_eps(X, np.polyfit, degree=3)
        # Propagate the resolved eps so sklearn internal state is consistent.
        super().__init__(
            eps=self.eps, min_samples=self.min_samples, metric=self.metric,
            metric_params=self.metric_params, algorithm=self.algorithm,
            leaf_size=self.leaf_size, p=self.p, n_jobs=self.n_jobs,
        )

    def fit(self, X, y=None, sample_weight=None):
        """Fit DBSCAN; resolves eps automatically when eps=None."""
        self._resolve_eps(X)
        return super().fit(X, y, sample_weight)

    def fit_predict(self, X, y=None, sample_weight=None):
        """Fit and return cluster labels; resolves eps automatically when eps=None."""
        self._resolve_eps(X)
        return super().fit_predict(X, y, sample_weight)