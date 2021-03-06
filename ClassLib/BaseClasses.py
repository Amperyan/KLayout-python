import pya
from math import sqrt, cos, sin, atan2, pi, copysign
from pya import Cell, Point, DPoint, DSimplePolygon, SimplePolygon, DPolygon, Polygon, Region
from pya import Trans, DTrans, CplxTrans, DCplxTrans, ICplxTrans

import ClassLib
from ClassLib._PROG_SETTINGS import *

from collections import OrderedDict


class ElementBase():
    def __init__(self, origin, trans_in=None):
        ## MUST BE IMPLEMENTED ##
        self.connections = []  # DPoint list with possible connection points
        self.angle_connections = []  # list with angle of connecting elements
        ## MUST BE IMLPEMENTED END ##

        self.connection_ptrs = []  # pointers to connected structures represented by their class instances

        self.origin = origin
        self.metal_region = Region()
        self.empty_region = Region()
        self.metal_regions = {}
        self.empty_regions = {}
        self.metal_regions["default"] = self.metal_region
        self.empty_regions["default"] = self.empty_region

        self.metal_region.merged_semantics = False
        self.empty_region.merged_semantics = False
        self.DCplxTrans_init = None
        self.ICplxTrans_init = None

        if (trans_in is not None):
            # if( isinstance( trans_in, ICplxTrans ) ): <==== FORBIDDEN
            if (isinstance(trans_in, DCplxTrans)):
                self.DCplxTrans_init = trans_in
                self.ICplxTrans_init = ICplxTrans().from_dtrans(trans_in)
            elif (isinstance(trans_in, CplxTrans)):
                self.DCplxTrans_init = DCplxTrans().from_itrans(trans_in)
                self.ICplxTrans_init = ICplxTrans().from_trans(trans_in)
            elif (isinstance(trans_in, DTrans)):
                self.DCplxTrans_init = DCplxTrans(trans_in, 1)
                self.ICplxTrans_init = ICplxTrans(Trans().from_dtrans(trans_in), 1)
            elif (isinstance(trans_in, Trans)):
                self.DCplxTrans_init = DCplxTrans(DTrans().from_itrans(trans_in), 1)
                self.ICplxTrans_init = ICplxTrans(trans_in, 1)

        self._init_regions_trans()

    def init_regions(self):
        raise NotImplementedError

    # first it makes trans_init displacement
    # then the rest of the trans_init
    # then displacement of the current state to the origin
    # after all, origin should be updated
    def _init_regions_trans(self):
        self.init_regions()  # must be implemented in every subclass
        dr_origin = DSimplePolygon([DPoint(0, 0)])
        if (self.DCplxTrans_init is not None):
            # constructor trans displacement
            dCplxTrans_temp = DCplxTrans(1, 0, False, self.DCplxTrans_init.disp)
            self.make_trans(dCplxTrans_temp)
            dr_origin.transform(dCplxTrans_temp)

            # rest of the constructor trans functions
            dCplxTrans_temp = self.DCplxTrans_init.dup()
            dCplxTrans_temp.disp = DPoint(0, 0)
            self.make_trans(dCplxTrans_temp)
            dr_origin.transform(dCplxTrans_temp)

        # translation to the old origin (self.connections are already contain proper values)
        self.make_trans(DCplxTrans(1, 0, False, self.origin))  # move to the origin
        self.origin += dr_origin.point(0)

    def make_trans(self, dCplxTrans):
        if (dCplxTrans is not None):
            iCplxTrans = ICplxTrans().from_dtrans(dCplxTrans)
            for metal_region, empty_region in zip(self.metal_regions.values(), self.empty_regions.values()):
                metal_region.transform(iCplxTrans)
                empty_region.transform(iCplxTrans)
            self._update_connections(dCplxTrans)
            self._update_alpha(dCplxTrans)

    def _update_connections(self, dCplxTrans):
        if (dCplxTrans is not None):
            # the problem is, if i construct polygon with multiple points
            # their order in poly_temp.each_point() doesn't coinside with the
            # order of the list that was passed to the polygon constructor
            # so, when i perform transformation and try to read new values through poly_temp.each_point()
            # they values are rearranged
            # solution is: i need to create polygon for each point personally, and the initial order presists
            for i, pt in enumerate(self.connections):
                poly_temp = DSimplePolygon([pt])
                poly_temp.transform(dCplxTrans)
                self.connections[i] = poly_temp.point(0)

    def _update_alpha(self, dCplxTrans):
        if (dCplxTrans is not None):
            dCplxTrans_temp = dCplxTrans.dup()
            dCplxTrans_temp.disp = DPoint(0, 0)

            for i, alpha in enumerate(self.angle_connections):
                poly_temp = DSimplePolygon([DPoint(cos(alpha), sin(alpha))])
                poly_temp.transform(dCplxTrans_temp)
                pt = poly_temp.point(0)
                self.angle_connections[i] = atan2(pt.y, pt.x)

    def _update_origin(self, dCplxTrans):
        if (dCplxTrans is not None):
            poly_temp = DSimplePolygon([self.origin])
            poly_temp.transform(dCplxTrans)
            self.origin = poly_temp.point(0)

    def place(self, dest, layer_i=None, region_name=None):

        if (region_name == None):
            metal_region = self.metal_region
            empty_region = self.empty_region
        else:
            metal_region = self.metal_regions[region_name]
            empty_region = self.empty_regions[region_name]

        if type(dest) is Cell and layer_i is not None:
            r_cell = Region(dest.begin_shapes_rec(layer_i))
            temp_i = dest.layout().layer(pya.LayerInfo(PROGRAM.LAYER1_NUM, 0))
            dest.shapes(temp_i).insert(r_cell + metal_region - empty_region)
            dest.layout().clear_layer(layer_i)
            dest.layout().move_layer(temp_i, layer_i)
            dest.layout().delete_layer(temp_i)

        elif type(dest) is Region:
            dest += metal_region
            dest -= empty_region

        # elif( layer_i == -1 ): # legacy behaviour
        #     print(type(dest))
        #
        #     for metal_region,empty_region in zip(self.metal_regions.values(),
        #                                             self.empty_regions.values()):
        #         dest += metal_region
        #         dest -= empty_region


class Complex_Base(ElementBase):
    def __init__(self, origin, trans_in=None):
        super().__init__(origin, trans_in)
        self.primitives = OrderedDict()
        self._init_primitives_trans()

    def _init_regions_trans(self):
        pass

    def make_trans(self, dCplxTrans_temp):

        # if type(self) is ClassLib.Coplanars.CPW_RL_Path:
        #    print("Make trans:", dCplxTrans_temp, self.connections)
        for primitive in self.primitives.values():
            primitive.make_trans(dCplxTrans_temp)

    def _init_primitives_trans(self):
        self.init_primitives()  # must be implemented in every subclass
        dr_origin = DSimplePolygon([DPoint(0, 0)])
        if (self.DCplxTrans_init is not None):
            # constructor trans displacement
            dCplxTrans_temp = DCplxTrans(1, 0, False, self.DCplxTrans_init.disp)
            for element in self.primitives.values():
                element.make_trans(dCplxTrans_temp)
            dr_origin.transform(dCplxTrans_temp)
            self._update_connections(dCplxTrans_temp)
            self._update_alpha(dCplxTrans_temp)

            # rest of the constructor trans functions
            dCplxTrans_temp = self.DCplxTrans_init.dup()
            dCplxTrans_temp.disp = DPoint(0, 0)
            for element in self.primitives.values():
                element.make_trans(dCplxTrans_temp)
            dr_origin.transform(dCplxTrans_temp)
            self._update_connections(dCplxTrans_temp)
            self._update_alpha(dCplxTrans_temp)

        dCplxTrans_temp = DCplxTrans(1, 0, False, self.origin)
        for element in self.primitives.values():
            element.make_trans(dCplxTrans_temp)  # move to the origin
        self._update_connections(dCplxTrans_temp)
        self._update_alpha(dCplxTrans_temp)
        self.origin += dr_origin.point(0)

        # FOLLOWING CYCLE GIVES WRONG INFO ABOUT FILLED AND ERASED AREAS
        for element in self.primitives.values():
            self.metal_region += element.metal_region
            self.empty_region += element.empty_region

    def place(self, dest, layer_i=None, region_name=None):

        if type(dest) is Cell and layer_i is not None:
            r_cell = Region(dest.begin_shapes_rec(layer_i))
            for primitive in self.primitives.values():
                primitive.place(r_cell)

            temp_i = dest.layout().layer(pya.LayerInfo(PROGRAM.LAYER1_NUM, 0))
            dest.shapes(temp_i).insert(r_cell)
            dest.layout().clear_layer(layer_i)
            dest.layout().move_layer(temp_i, layer_i)
            dest.layout().delete_layer(temp_i)

        elif region_name is None:
            for primitive in self.primitives.values():
                primitive.place(dest)
        else:
            for primitive in self.primitives.values():
                primitive.place(dest, region_name=region_name)

    def init_primitives(self):
        raise NotImplementedError

    def init_regions(self):
        pass


#### TEMPLATE SAVINGS ####

'''
class ElementBase():
    def __init__(self, origin, trans_in=None):
        ## MUST BE IMPLEMENTED ##
        self.connections = []       # DPoint list with possible connection points
        self.angle_connections = [] #list with angle of connecting elements
        self.connection_ptrs = [] # pointers to connected structures represented by their class instances
        ## MUST BE IMLPEMENTED END ##
        self.origin = origin
        self.metal_region = Region()
        self.empty_region = Region()
        self.metal_regions = {}
        self.empty_regions = {}

        self.metal_region.merged_semantics = False
        self.empty_region.merged_semantics = False
        self.DCplxTrans_init = None
        self.ICplxTrans_init = None

        if( trans_in is not None ):
        # if( isinstance( trans_in, ICplxTrans ) ): <==== FORBIDDEN
            if( isinstance( trans_in, DCplxTrans ) ):
                self.DCplxTrans_init = trans_in
                self.ICplxTrans_init = ICplxTrans().from_dtrans( trans_in )
            elif( isinstance( trans_in, CplxTrans ) ):
                self.DCplxTrans_init = DCplxTrans().from_itrans( trans_in )
                self.ICplxTrans_init = ICplxTrans().from_trans( trans_in )
            elif( isinstance( trans_in, DTrans ) ):
                self.DCplxTrans_init = DCplxTrans( trans_in, 1 )
                self.ICplxTrans_init = ICplxTrans( Trans().from_dtrans( trans_in ), 1 )
            elif( isinstance( trans_in, Trans ) ):
                self.DCplxTrans_init = DCplxTrans( DTrans().from_itrans( trans_in ), 1 )
                self.ICplxTrans_init = ICplxTrans( trans_in, 1 )

        self._init_regions_trans()

    def init_regions( self ):
        raise NotImplementedError

    # first it makes trans_init displacement
    # then the rest of the trans_init
    # then displacement of the current state to the origin
    # after all, origin should be updated
    def _init_regions_trans( self ):
        self.init_regions()         # must be implemented in every subclass
        dr_origin = DSimplePolygon( [DPoint(0,0)] )
        if( self.DCplxTrans_init is not None ):
            # constructor trans displacement
            dCplxTrans_temp = DCplxTrans( 1,0,False, self.DCplxTrans_init.disp )
            self.make_trans( dCplxTrans_temp )
            dr_origin.transform( dCplxTrans_temp )

            # rest of the constructor trans functions
            dCplxTrans_temp = self.DCplxTrans_init.dup()
            dCplxTrans_temp.disp = DPoint(0,0)
            self.make_trans( dCplxTrans_temp )
            dr_origin.transform( dCplxTrans_temp )

        # translation to the old origin (self.connections are alredy contain proper values)
        self.make_trans( DCplxTrans( 1,0,False, self.origin ) ) # move to the origin
        self.origin += dr_origin.point( 0 )

    def make_trans( self, dCplxTrans ):
        if( dCplxTrans is not None ):
            iCplxTrans = ICplxTrans().from_dtrans( dCplxTrans )
            self.metal_region.transform( iCplxTrans )
            self.empty_region.transform( iCplxTrans )
            self._update_connections( dCplxTrans )
            self._update_alpha( dCplxTrans )

    def _update_connections( self, dCplxTrans ):
        if( dCplxTrans is not None ):
            # the problem is, if i construct polygon with multiple points
            # their order in poly_temp.each_point() doesn't coinside with the
            # order of the list that was passed to the polygon constructor
            # so, when i perform transformation and try to read new values through poly_temp.each_point()
            # they values are rearranged
            # solution is: i need to create polygon for each point personally, and the initial order presists
            for i,pt in enumerate(self.connections):
                poly_temp = DSimplePolygon( [pt] )
                poly_temp.transform( dCplxTrans )
                self.connections[i] = poly_temp.point( 0 )

    def _update_alpha( self, dCplxTrans ):
        if( dCplxTrans is not None ):
            dCplxTrans_temp = dCplxTrans.dup()
            dCplxTrans_temp.disp = DPoint(0,0)

            for i,alpha in enumerate(self.angle_connections):
                poly_temp = DSimplePolygon( [DPoint( cos(alpha), sin(alpha) )] )
                poly_temp.transform( dCplxTrans_temp )
                pt = poly_temp.point( 0 )
                self.angle_connections[i] = atan2( pt.y, pt.x )

    def _update_origin( self, dCplxTrans ):
        if( dCplxTrans is not None ):
            poly_temp = DSimplePolygon( [self.origin] )
            poly_temp.transform( dCplxTrans )
            self.origin = poly_temp.point( 0 )

    def place( self, dest, layer_i=-1 ):
        r_cell = None
        if( layer_i != -1 ):
            r_cell = Region( dest.begin_shapes_rec( layer_i ) )
        # how to interpret destination
        if( layer_i == -1 ):
            dest += self.metal_region
            dest -= self.empty_region
        else:
            temp_i = dest.layout().layer( pya.LayerInfo(PROGRAM.LAYER1_NUM,0) )
            dest.shapes( temp_i ).insert( r_cell + self.metal_region  - self.empty_region )
            dest.layout().clear_layer( layer_i )
            dest.layout().move_layer( temp_i, layer_i )
            dest.layout().delete_layer( temp_i )
            '''
