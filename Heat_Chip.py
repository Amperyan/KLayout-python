import pya
from importlib import reload
import ClassLib
from ClassLib import *

reload(BaseClasses)
reload(Capacitors)
reload(Coplanars)
reload(JJ)
reload(Qbits)
reload(Resonators)
reload(Shapes)
reload(ContactPad)
reload(Claw)
reload(Tmon)
reload(FluxCoil)
reload(_PROG_SETTINGS)
from ClassLib import *

from ClassLib.ContactPad import *
from ClassLib.Claw import *
from ClassLib.Resonators import *
from ClassLib.Tmon import *
from ClassLib.FluxCoil import *

from time import time

class CHIP:
    dx = 10e6
    dy = 5e6


app = pya.Application.instance()
mw = app.main_window()
lv = mw.current_view()
cv = None

#this insures that lv and cv are valid objects
if( lv == None ):
    cv = mw.create_layout(1)
    lv = mw.current_view()
else:
    cv = lv.active_cellview()

layout = cv.layout()
layout.dbu = 0.001
if( layout.has_cell( "testScript") ):
    pass
else:
    cell = layout.create_cell( "testScript" )


info = pya.LayerInfo(1,0)
info2 = pya.LayerInfo(2,0)
layer_photo = layout.layer( info )
layer_el = layout.layer( info2 )

# clear this cell and layer
cell.clear()

# setting layout view
lv.select_cell(cell.cell_index(), 0)
lv.add_missing_layers()


#Constants

ground = pya.Box(Point(-CHIP.dx/2, -CHIP.dy/2), Point(CHIP.dx/2, CHIP.dy/2))
canvas = Region(ground)

ebeam = Region()

feed_cpw_params = CPWParameters(20e3, 10e3)
md_cpw_params = CPWParameters(7e3, 4e3)
fc_cpw_params = CPWParameters(7e3, 4e3)

### DRAW SECTION START ###

#feedline contacts
cp_feed_1 = Contact_Pad(origin = DPoint(-CHIP.dx/6,-CHIP.dy/2), feedline_cpw_params = feed_cpw_params, trans_in = DTrans.R90)
cp_feed_1.place(canvas)

cp_feed_2 = Contact_Pad(origin = DPoint(CHIP.dx/6,-CHIP.dy/2), feedline_cpw_params = feed_cpw_params, trans_in = DTrans.R90)
cp_feed_2.place(canvas)

#termometer contacts
cp_term_1 = Contact_Pad(origin = DPoint(-CHIP.dx/2,+CHIP.dy/4), feedline_cpw_params = md_cpw_params)
cp_term_1.place(canvas)

cp_term_2 = Contact_Pad(origin = DPoint(-CHIP.dx/6,+CHIP.dy/2), feedline_cpw_params = md_cpw_params, trans_in = DTrans.R270)
cp_term_2.place(canvas)

cp_term_3 = Contact_Pad(origin = DPoint(-CHIP.dx/3,+CHIP.dy/2), feedline_cpw_params = md_cpw_params, trans_in = DTrans.R270)
cp_term_3.place(canvas)

#flux contact
cp_fc = Contact_Pad(origin = DPoint(CHIP.dx/6,+CHIP.dy/2), feedline_cpw_params = md_cpw_params, trans_in = DTrans.R270)
cp_fc.place(canvas)

#microwave drive contact
cp_md = Contact_Pad(origin = DPoint(CHIP.dx/3,+CHIP.dy/2), feedline_cpw_params = md_cpw_params, trans_in = DTrans.R270)
cp_md.place(canvas)

# ======== Main feedline =========

turn_rad = 0.24e6
feed_segment_lenghts = [turn_rad, 2.5e6, 0.5e6, 5e6 - cp_feed_1.end.x + cp_feed_2.end.x, 0.5e6, 2.5e6, turn_rad]

feedline = CPW_RL_Path(cp_feed_2.end, "LRLRLRLRLRLRL", feed_cpw_params, turn_rad,
     feed_segment_lenghts, [-pi/2, +pi/2, +pi/2, +pi/2, +pi/2, -pi/2] ,trans_in = DTrans.R90)
feedline.place(canvas)


# ======= Chain loop =========

resonator_offsets = 5e3
res_cpw_params = CPWParameters(7e3, 4e3)
tmon_cpw_params = CPWParameters(20e3, 20e3)

resonators_site_span = cp_feed_2.end.x - cp_feed_1.end.x

resonators_y_positions = cp_feed_2.end.y + turn_rad*3 + feed_cpw_params.b+res_cpw_params.b/2+resonator_offsets

tmon_arm_len = 280e3
tmon_JJ_arm_len = 40e3
tmon_JJ_site_span = 8e3
tmon_coupling_pads_len = 100e3
h_jj = 200
w_jj = 100
asymmetry = 0.5

qubit_x = 0e3
qubit_y = 100e3
claw_len = 200e3 


#readout resonator drawing
claw = Claw(DPoint(qubit_x,qubit_y), res_cpw_params, claw_len, w_claw = 20e3, w_claw_pad=0e3, l_claw_pad = 0e3)
coupling_length = 200e3
res_cursor = DPoint(0, resonators_y_positions)

res = CPWResonator(res_cursor, res_cpw_params, 40e3, 6+(0+4)/10, 11.45,\
                    coupling_length=450e3,meander_periods = 3, trans_in = trans_in)
claw.make_trans(DTrans(res.end))
claw.place(canvas)
res.place(canvas)

#qubit drawing
tmon = Tmon(claw.connections[1], tmon_cpw_params, tmon_arm_len, \
            tmon_JJ_arm_len, tmon_JJ_site_span, tmon_coupling_pads_len, \
            h_jj, w_jj, asymmetry, None)

tmon.place(canvas, region_name = "photo")
tmon.place(ebeam, region_name = "ebeam")


qubit_ports.append(tmon.end)




#i=-6
#for i in range(-(chain_length)//2, (chain_length)//2, 1):
  #coupling_length = 200e3
 # res_cursor = DPoint(i*resonators_interval+resonators_interval/2, resonators_y_positions)
 # print(i)
 # trans_in = None if i>=0 else DTrans.M90
 # claw = Claw(DPoint(0,0), res_cpw_params, 200e3, w_claw = 20e3, w_claw_pad=0, l_claw_pad = 0)
  #res = CPWResonator(res_cursor, res_cpw_params, 40e3, 6+(i+4)/10, 11.45, coupling_length=450e3,
 #                                   meander_periods = 3, trans_in = trans_in)
#  claw.make_trans(DTrans(res.end))
 # claw.place(canvas)
 # res.place(canvas)

  #tmon = Tmon(claw.connections[1], tmon_cpw_params, tmon_arm_len, \
     #           tmon_JJ_arm_len, tmon_JJ_site_span, tmon_coupling_pads_len, \
    #              h_jj, w_jj, asymmetry, None)

 # tmon.place(canvas, region_name = "photo")
  #tmon.place(ebeam, region_name = "ebeam")


 # qubit_ports.append(tmon.end)




ebeam = ebeam.merge()
cell.shapes( layer_photo ).insert(canvas)
cell.shapes( layer_el ).insert(ebeam)



lv.zoom_fit()
