try:
    import scipy.sparse
    _scipy_available = True
except ImportError:
    _scipy_available = False

import cupy
from cupy import cusparse
from cupy.sparse import base
from cupy.sparse import compressed
from cupy.sparse import csc


class csr_matrix(compressed._compressed_sparse_matrix):

    """Compressed Sparse Row matrix.

    Now it has only part of initializer formats:

    ``csr_matrix(S)``
        ``S`` is another sparse matrix. It is equivalent to ``S.tocsr()``.
    ``csr_matrix((data, indices, indptr))``
        All ``data``, ``indices`` and ``indptr`` are one-dimenaional
        :class:`cupy.ndarray`.

    Args:
        arg1: Arguments for the initializer.
        shape (tuple): Shape of a matrix. Its length must be two.
        dtype: Data type. It must be an argument of :class:`numpy.dtype`.
        copy (bool): If ``True``, copies of given arrays are always used.

    .. see::
       :class:`scipy.sparse.csr_matrix`

    """

    format = 'csr'

    # TODO(unno): Implement has_sorted_indices

    def get(self, stream=None):
        """Returns a copy of the array on host memory.

        Args:
            stream (cupy.cuda.Stream): CUDA stream object. If it is given, the
                copy runs asynchronously. Otherwise, the copy is synchronous.

        Returns:
            scipy.sparse.csr_matrix: Copy of the array on host memory.

        """
        if not _scipy_available:
            raise RuntimeError('scipy is not available')
        data = self.data.get(stream)
        indices = self.indices.get(stream)
        indptr = self.indptr.get(stream)
        return scipy.sparse.csr_matrix(
            (data, indices, indptr), shape=self._shape)

    def _swap(self, x, y):
        return (x, y)

    # TODO(unno): Implement __getitem__

    def _add_sparse(self, other, alpha, beta):
        return cusparse.csrgeam(self, other.tocsr(), alpha, beta)

    def __mul__(self, other):
        if cupy.isscalar(other):
            return self._with_data(self.data * other)
        elif isspmatrix_csr(other):
            return cusparse.csrgemm(self, other)
        elif csc.isspmatrix_csc(other):
            return cusparse.csrgemm(self, other.T, transb=True)
        elif base.isspmatrix(other):
            return cusparse.csrgemm(self, other.tocsr())
        elif base.isdense(other):
            if other.ndim == 0:
                return self._with_data(self.data * other)
            elif other.ndim == 1:
                return cusparse.csrmv(self, other)
            elif other.ndim == 2:
                return cusparse.csrmm2(self, other)
            else:
                raise ValueError('could not interpret dimensions')
        else:
            return NotImplemented

    # TODO(unno): Implement argmax
    # TODO(unno): Implement argmin
    # TODO(unno): Implement check_format
    # TODO(unno): Implement diagonal
    # TODO(unno): Implement dot
    # TODO(unno): Implement eliminate_zeros

    # TODO(unno): Implement max
    # TODO(unno): Implement maximum
    # TODO(unno): Implement min
    # TODO(unno): Implement minimum
    # TODO(unno): Implement multiply
    # TODO(unno): Implement prune
    # TODO(unno): Implement reshape

    def sort_indices(self):
        """Sorts the indices of the matrix in place."""
        cusparse.csrsort(self)

    # TODO(unno): Implement sum_duplicates

    def toarray(self, order=None, out=None):
        """Returns a dense matrix representing the same value.

        Args:
            order (str): Not supported.
            out: Not supported.

        Returns:
            cupy.ndarray: Dense array representing the same matrix.

        .. seealso:: :func:`cupy.sparse.csr_array.toarray`

        """
        # csr2dense returns F-contiguous array.
        # To return C-contiguous array, it uses transpose.
        return cusparse.csc2dense(self.T).T

    # TODO(unno): Implement tobsr

    def tocoo(self, copy=False):
        """Converts the matrix to COOdinate format.

        Args:
            copy (bool): If ``False``, it shares data arrays as much as
                possible.

        Returns:
            cupy.sparse.coo_matrix: Converted matrix.

        """
        if copy:
            data = self.data.copy()
            indices = self.indices.copy()
        else:
            data = self.data
            indices = self.indices

        return cusparse.csr2coo(self, data, indices)

    def tocsc(self, copy=False):
        """Converts the matrix to Compressed Sparse Column format.

        Args:
            copy (bool): If ``False``, it shares data arrays as much as
                possible. Actually this option is ignored because all
                arrays in a matrix cannot be shared in csr to csc conversion.

        Returns:
            cupy.sparse.csc_matrix: Converted matrix.

        """
        # copy is ignored
        return cusparse.csr2csc(self)

    def tocsr(self, copy=None):
        """Converts the matrix to Compressed Sparse Row format.

        Args:
            copy: Not supported yet.

        Returns:
            cupy.sparse.csr_matrix: Converted matrix.

        """
        return self

    # TODO(unno): Implement todia
    # TODO(unno): Implement todok
    # TODO(unno): Implement tolil

    def transpose(self, axes=None, copy=False):
        """Returns a transpose matrix.

        Args:
            axes: This option is not supported.
            copy (bool): If ``True``, a returned matrix shares no data.
                Otherwise, it shared data arrays as much as possible.

        Returns:
            cupy.sparse.spmatrix: Transpose matrix.

        """
        if axes is not None:
            raise ValueError(
                'Sparse matrices do not support an \'axes\' parameter because '
                'swapping dimensions is the only logical permutation.')

        shape = self.shape[1], self.shape[0]
        return csc.csc_matrix(
            (self.data, self.indices, self.indptr), shape=shape, copy=copy)


def isspmatrix_csr(x):
    """Checks if a given matrix is of CSR format.

    Returns:
        bool: Returns if ``x`` is :class:`cupy.sparse.csr_matrix`.

    """
    return isinstance(x, csr_matrix)
