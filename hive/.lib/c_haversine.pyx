import numpy as np
from cython.parallel import prange
from libc.math cimport sin, cos, asin, sqrt

cdef double DEG_TO_RAD = 3.1415926536 / 180
cdef double R = 6371

cdef inline double haversine(double lat1, double lon1, double lat2, double lon2) nogil:
  cdef double dx, dy, dz
  lon1 -= lon2
  lon1 *= DEG_TO_RAD
  lat1 *= DEG_TO_RAD
  lat2 *= DEG_TO_RAD

  dz = sin(lat1) - sin(lat2)
  dx = cos(lon1) * cos(lat1) - cos(lat2)
  dy = sin(lon1) * cos(lat1)

  return asin(sqrt(dx * dx + dy * dy + dz * dz) / 2) * 2 * R

def single_haversine(double lat1, double lon1, double lat2, double lon2):
  return haversine(lat1, lon1, lat2, lon2)

def vector_haversine(double[:] LAT, double[:] LON, double[:] point, int N):
  cdef int i
  cdef double[:] dist = np.zeros(N)

  for i in range(N):
    dist[i] = haversine(LAT[i], LON[i], point[0], point[1])

  return dist

def vector_haversine_parallel(double[:] LAT, double[:] LON, double[:] point, int N):
  cdef int i
  cdef double[:] dist = np.zeros(N)

  for i in prange(N, nogil=True):
    dist[i] = haversine(LAT[i], LON[i], point[0], point[1])

  return dist
