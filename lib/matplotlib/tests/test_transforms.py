from __future__ import print_function
import unittest

from nose.tools import assert_equal
import numpy.testing as np_test, assert_almost_equal
from matplotlib.transforms import Affine2D, BlendedGenericTransform
from matplotlib.path import Path
from matplotlib.scale import LogScale
from matplotlib.testing.decorators import cleanup, image_comparison
import numpy as np

import matplotlib.transforms as mtrans
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.patches as mpatches



@cleanup
def test_non_affine_caching():
    class AssertingNonAffineTransform(mtrans.Transform):
        """
        This transform raises an assertion error when called when it
        shouldn't be and self.raise_on_transform is True.

        """
        input_dims = output_dims = 2
        is_affine = False
        def __init__(self, *args, **kwargs):
            mtrans.Transform.__init__(self, *args, **kwargs)
            self.raise_on_transform = False
            self.underlying_transform = mtrans.Affine2D().scale(10, 10)

        def transform_path_non_affine(self, path):
            if self.raise_on_transform:
                assert False, ('Invalidated affine part of transform '
                                    'unnecessarily.')
            return self.underlying_transform.transform_path(path)
        transform_path = transform_path_non_affine

        def transform_non_affine(self, path):
            if self.raise_on_transform:
                assert False, ('Invalidated affine part of transform '
                                    'unnecessarily.')
            return self.underlying_transform.transform(path)
        transform = transform_non_affine

    my_trans = AssertingNonAffineTransform()
    ax = plt.axes()
    plt.plot(range(10), transform=my_trans + ax.transData)
    plt.draw()
    # enable the transform to raise an exception if it's non-affine transform
    # method is triggered again.
    my_trans.raise_on_transform = True
    ax.transAxes.invalidate()
    plt.draw()


@cleanup
def test_external_transform_api():
    class ScaledBy(object):
        def __init__(self, scale_factor):
            self._scale_factor = scale_factor
            
        def _as_mpl_transform(self, axes):
            return mtrans.Affine2D().scale(self._scale_factor) + axes.transData

    ax = plt.axes()
    line, = plt.plot(range(10), transform=ScaledBy(10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    # assert that the top transform of the line is the scale transform.
    np.testing.assert_allclose(line.get_transform()._a.get_matrix(), 
                               mtrans.Affine2D().scale(10).get_matrix())
    

@image_comparison(baseline_images=['pre_transform_data'])
def test_pre_transform_plotting():
    # a catch-all for as many as possible plot layouts which handle pre-transforming the data
    # NOTE: The axis range is important in this plot. It should be x10 what the data suggests it should be 
    ax = plt.axes()
    times10 = mtrans.Affine2D().scale(10)
    
    ax.contourf(np.arange(48).reshape(6, 8), transform=times10 + ax.transData)
    
    ax.pcolormesh(np.linspace(0, 4, 7), 
                  np.linspace(5.5, 8, 9), 
                  np.arange(48).reshape(6, 8),
                  transform=times10 + ax.transData)
    
    ax.scatter(np.linspace(0, 10), np.linspace(10, 0), 
               transform=times10 + ax.transData)
    
    
    x = np.linspace(8, 10, 20)
    y = np.linspace(1, 5, 20)
    u = 2*np.sin(x) + np.cos(y[:, np.newaxis])
    v = np.sin(x) - np.cos(y[:, np.newaxis])

    ax.streamplot(x, y, u, v, transform=times10 + ax.transData,
                  density=(1, 1), linewidth=u**2 + v**2)
    
    # reduce the vector data down a bit for barb and quiver plotting
    x, y = x[::3], y[::3]
    u, v = u[::3, ::3], v[::3, ::3]
    
    ax.quiver(x, y + 5, u, v, transform=times10 + ax.transData)
    
    ax.barbs(x - 3, y + 5, u**2, v**2, transform=times10 + ax.transData)
    

def test_Affine2D_from_values():
    points = np.array([ [0,0],
               [10,20],
               [-1,0],
               ])

    t = mtrans.Affine2D.from_values(1,0,0,0,0,0)
    actual = t.transform(points)
    expected = np.array( [[0,0],[10,0],[-1,0]] )
    assert_almost_equal(actual,expected)

    t = mtrans.Affine2D.from_values(0,2,0,0,0,0)
    actual = t.transform(points)
    expected = np.array( [[0,0],[0,20],[0,-2]] )
    assert_almost_equal(actual,expected)

    t = mtrans.Affine2D.from_values(0,0,3,0,0,0)
    actual = t.transform(points)
    expected = np.array( [[0,0],[60,0],[0,0]] )
    assert_almost_equal(actual,expected)

    t = mtrans.Affine2D.from_values(0,0,0,4,0,0)
    actual = t.transform(points)
    expected = np.array( [[0,0],[0,80],[0,0]] )
    assert_almost_equal(actual,expected)

    t = mtrans.Affine2D.from_values(0,0,0,0,5,0)
    actual = t.transform(points)
    expected = np.array( [[5,0],[5,0],[5,0]] )
    assert_almost_equal(actual,expected)

    t = mtrans.Affine2D.from_values(0,0,0,0,0,6)
    actual = t.transform(points)
    expected = np.array( [[0,6],[0,6],[0,6]] )
    assert_almost_equal(actual,expected)


def test_clipping_of_log():
    # issue 804
    M,L,C = Path.MOVETO, Path.LINETO, Path.CLOSEPOLY
    points = [ (0.2, -99), (0.4, -99), (0.4, 20), (0.2, 20), (0.2, -99) ]
    codes  = [          M,          L,        L,         L,          C  ]
    path = Path(points, codes)

    # something like this happens in plotting logarithmic histograms
    trans = BlendedGenericTransform(Affine2D(),
                                    LogScale.Log10Transform('clip'))
    tpath = trans.transform_path_non_affine(path)
    result = tpath.iter_segments(trans.get_affine(),
                                 clip=(0, 0, 100, 100),
                                 simplify=False)

    tpoints, tcodes = zip(*result)
    # Because y coordinate -99 is outside the clip zone, the first
    # line segment is effectively removed. That means that the closepoly
    # operation must be replaced by a move to the first point.
    assert np.allclose(tcodes, [ M, M, L, L, L ])
    assert np.allclose(tpoints[-1], tpoints[0])


class NonAffineForTest(mtrans.Transform):
    """
    A class which looks like a non affine transform, but does whatever
    the given transform does (even if it is affine). This is very useful
    for testing NonAffine behaviour with a simple Affine transform.

    """
    is_affine = False
    output_dims = 2
    input_dims = 2

    def __init__(self, real_trans, *args, **kwargs):
        self.real_trans = real_trans
        r = mtrans.Transform.__init__(self, *args, **kwargs)

    def transform_non_affine(self, values):
        return self.real_trans.transform(values)

    def transform_path_non_affine(self, path):
        return self.real_trans.transform_path(path)


class BasicTransformTests(unittest.TestCase):
    def setUp(self):

        self.ta1 = mtrans.Affine2D(shorthand_name='ta1').rotate(np.pi / 2)
        self.ta2 = mtrans.Affine2D(shorthand_name='ta2').translate(10, 0)
        self.ta3 = mtrans.Affine2D(shorthand_name='ta3').scale(1, 2)

        self.tn1 = NonAffineForTest(mtrans.Affine2D().translate(1, 2), shorthand_name='tn1')
        self.tn2 = NonAffineForTest(mtrans.Affine2D().translate(1, 2), shorthand_name='tn2')
        self.tn3 = NonAffineForTest(mtrans.Affine2D().translate(1, 2), shorthand_name='tn3')

        # creates a transform stack which looks like ((A, (N, A)), A)
        self.stack1 = (self.ta1 + (self.tn1 + self.ta2)) + self.ta3
        # creates a transform stack which looks like (((A, N), A), A)
        self.stack2 = self.ta1 + self.tn1 + self.ta2 + self.ta3
        # creates a transform stack which is a subset of stack2
        self.stack2_subset = self.tn1 + self.ta2 + self.ta3

        # when in debug, the transform stacks can produce dot images:
#        self.stack1.write_graphviz(file('stack1.dot', 'w'))
#        self.stack2.write_graphviz(file('stack2.dot', 'w'))
#        self.stack2_subset.write_graphviz(file('stack2_subset.dot', 'w'))

    def test_left_to_right_iteration(self):
        stack3 = (self.ta1 + (self.tn1 + (self.ta2 + self.tn2))) + self.ta3
#        stack3.write_graphviz(file('stack3.dot', 'w'))

        target_transforms = [stack3,
                             (self.tn1 + (self.ta2 + self.tn2)) + self.ta3,
                             (self.ta2 + self.tn2) + self.ta3,
                             self.tn2 + self.ta3,
                             self.ta3,
                             ]
        r = [rh for lh, rh in stack3._iter_break_from_left_to_right()]
        self.assertEqual(len(r), len(target_transforms))

        for target_stack, stack in zip(target_transforms, r):
            self.assertEqual(target_stack, stack)

    def test_transform_shortcuts(self):
        self.assertEqual(self.stack1 - self.stack2_subset, self.ta1)
        self.assertEqual(self.stack2 - self.stack2_subset, self.ta1)

        # check that we cannot find a chain from the subset back to the superset
        # (since the inverse of the Transform is not defined.)
        self.assertRaises(ValueError, self.stack2_subset.__sub__, self.stack2)
        self.assertRaises(ValueError, self.stack1.__sub__, self.stack2)

        aff1 = self.ta1 + (self.ta2 + self.ta3)
        aff2 = self.ta2 + self.ta3

        self.assertEqual(aff1 - aff2, self.ta1)
        self.assertEqual(aff1 - self.ta2, aff1 + self.ta2.inverted())

        self.assertEqual(self.stack1 - self.ta3, self.ta1 + (self.tn1 + self.ta2))
        self.assertEqual(self.stack2 - self.ta3, self.ta1 + self.tn1 + self.ta2)
        
        self.assertEqual((self.ta2 + self.ta3) - self.ta3 + self.ta3, self.ta2 + self.ta3)

    def test_contains_branch(self):
        r1 = (self.ta2 + self.ta1)
        r2 = (self.ta2 + self.ta1)
        self.assertEqual(r1, r2)
        self.assertNotEqual(r1, self.ta1)
        self.assertTrue(r1.contains_branch(r2))
        self.assertTrue(r1.contains_branch(self.ta1))
        self.assertFalse(r1.contains_branch(self.ta2))
        self.assertFalse(r1.contains_branch((self.ta2 + self.ta2)))

        self.assertEqual(r1, r2)

        self.assertTrue(self.stack1.contains_branch(self.ta3))
        self.assertTrue(self.stack2.contains_branch(self.ta3))

        self.assertTrue(self.stack1.contains_branch(self.stack2_subset))
        self.assertTrue(self.stack2.contains_branch(self.stack2_subset))

        self.assertFalse(self.stack2_subset.contains_branch(self.stack1))
        self.assertFalse(self.stack2_subset.contains_branch(self.stack2))

        self.assertTrue(self.stack1.contains_branch((self.ta2 + self.ta3)))
        self.assertTrue(self.stack2.contains_branch((self.ta2 + self.ta3)))

        self.assertFalse(self.stack1.contains_branch((self.tn1 + self.ta2)))

    def test_affine_simplification(self):
        # tests that a transform stack only calls as much is absolutely necessary
        # "non-affine" allowing the best possible optimization with complex
        # transformation stacks.
        points = np.array([[0, 0], [10, 20], [np.nan, 1], [-1, 0]], dtype=np.float64)
        na_pts = self.stack1.transform_non_affine(points)
        all_pts = self.stack1.transform(points)

        na_expected = np.array([[1., 2.], [-19., 12.],
                                [np.nan, np.nan], [1., 1.]], dtype=np.float64)
        all_expected = np.array([[11., 4.], [-9., 24.],
                                 [np.nan, np.nan], [11., 2.]], dtype=np.float64)

        # check we have the expected results from doing the affine part only
        np_test.assert_array_almost_equal(na_pts, na_expected)
        # check we have the expected results from a full transformation
        np_test.assert_array_almost_equal(all_pts, all_expected)
        # check we have the expected results from doing the transformation in two steps
        np_test.assert_array_almost_equal(self.stack1.transform_affine(na_pts), all_expected)
        # check that getting the affine transformation first, then fully transforming using that
        # yields the same result as before.
        np_test.assert_array_almost_equal(self.stack1.get_affine().transform(na_pts), all_expected)

        # check that the affine part of stack1 & stack2 are equivalent (i.e. the optimization
        # is working)
        expected_result = (self.ta2 + self.ta3).get_matrix()
        result = self.stack1.get_affine().get_matrix()
        np_test.assert_array_equal(expected_result, result)

        result = self.stack2.get_affine().get_matrix()
        np_test.assert_array_equal(expected_result, result)


class TestTransformPlotInterface(unittest.TestCase):
    def tearDown(self):
        plt.close()

    def test_line_extents_affine(self):
        ax = plt.axes()
        offset = mtrans.Affine2D().translate(10, 10)
        plt.plot(range(10), transform=offset + ax.transData)
        expeted_data_lim = np.array([[0., 0.], [9.,  9.]]) + 10
        np.testing.assert_array_almost_equal(ax.dataLim.get_points(),
                                             expeted_data_lim)

    def test_line_extents_non_affine(self):
        ax = plt.axes()
        offset = mtrans.Affine2D().translate(10, 10)
        na_offset = NonAffineForTest(mtrans.Affine2D().translate(10, 10))
        plt.plot(range(10), transform=offset + na_offset + ax.transData)
        expeted_data_lim = np.array([[0., 0.], [9.,  9.]]) + 20
        np.testing.assert_array_almost_equal(ax.dataLim.get_points(),
                                             expeted_data_lim)

    def test_pathc_extents_non_affine(self):
        ax = plt.axes()
        offset = mtrans.Affine2D().translate(10, 10)
        na_offset = NonAffineForTest(mtrans.Affine2D().translate(10, 10))
        pth = mpath.Path(np.array([[0, 0], [0, 10], [10, 10], [10, 0]]))
        patch = mpatches.PathPatch(pth, transform=offset + na_offset + ax.transData)
        ax.add_patch(patch)
        expeted_data_lim = np.array([[0., 0.], [10.,  10.]]) + 20
        np.testing.assert_array_almost_equal(ax.dataLim.get_points(),
                                             expeted_data_lim)

    def test_pathc_extents_affine(self):
        ax = plt.axes()
        offset = mtrans.Affine2D().translate(10, 10)
        pth = mpath.Path(np.array([[0, 0], [0, 10], [10, 10], [10, 0]]))
        patch = mpatches.PathPatch(pth, transform=offset + ax.transData)
        ax.add_patch(patch)
        expeted_data_lim = np.array([[0., 0.], [10.,  10.]]) + 10
        np.testing.assert_array_almost_equal(ax.dataLim.get_points(), 
                                             expeted_data_lim)


    def test_line_extents_for_non_affine_transData(self):
        ax = plt.axes(projection='polar')
        # add 10 to the radius of the data
        offset = mtrans.Affine2D().translate(0, 10)

        plt.plot(range(10), transform=offset + ax.transData)
        # the data lim of a polar plot is stored in coordinates
        # before a transData transformation, hence the data limits
        # are not what is being shown on the actual plot.
        expeted_data_lim = np.array([[0., 0.], [9.,  9.]]) + [0, 10]
        np.testing.assert_array_almost_equal(ax.dataLim.get_points(),
                                             expeted_data_lim)


if __name__=='__main__':
    import nose
    nose.runmodule(argv=['-s','--with-doctest'], exit=False)