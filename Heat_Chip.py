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
cp_md = Contact_Pad(origin = DPoint(CHIP.dx/2,+CHIP.dy/4), feedline_cpw_params = md_cpw_params, trans_in = DTrans.R180)
cp_md.place(canvas)

# ======== Main feedline =========

turn_rad = 0.24e6
feed_segment_lenghts = [turn_rad, 2.5e6, 0.5e6, 5e6 - cp_feed_1.end.x + cp_feed_2.end.x, 0.5e6, 2.5e6, turn_rad]

feedline = CPW_RL_Path(cp_feed_2.end, "LRLRLRLRLRLRL", feed_cpw_params, turn_rad,
     feed_segment_lenghts, [-pi/2, +pi/2, +pi/2, +pi/2, +pi/2, -pi/2] ,trans_in = DTrans.R90)
feedline.place(canvas)


# ======= Chain loop =========


res_cpw_params = CPWParameters(7e3, 4e3)
tmon_cpw_params = CPWParameters(20e3, 20e3)

qubit_x = cp_fc.end.x
qubit_y = 500e3


#======= Claw drawing =========
claw_len = 200e3 
claw = Claw(DPoint(qubit_x,qubit_y), res_cpw_params, claw_len, w_claw = 20e3, w_claw_pad=0e3, l_claw_pad = 0e3)
claw.place(canvas)


#====== Readout resonator drawing ======
coupling_length = 200e3
resonator_offsets = 5e3
resonator_turn_radius = 40e3
resonator_freq = 6.5 #GGZ
meander_periods = 3
#neck_length = 200e3
offset_length = 200e3
coupling_length = 450e3

resonators_y_positions = cp_feed_2.end.y + turn_rad*3 + feed_cpw_params.b\
                          +res_cpw_params.b/2+resonator_offsets
                          
                          
neck_length = qubit_y - 4*resonator_turn_radius*meander_periods -\
             5*resonator_turn_radius - offset_length - resonators_y_positions


res_cursor = DPoint(qubit_x, resonators_y_positions)

res = CPWResonator(res_cursor, res_cpw_params, resonator_turn_radius, resonator_freq, 11.45,\
                  coupling_length = coupling_length, meander_periods = meander_periods,\
                  neck_length = neck_length, offset_length = offset_length, trans_in = trans_in)
res.place(canvas)


#====== Qubit drawing ============
tmon_arm_len = 280e3
tmon_JJ_arm_len = 40e3
tmon_JJ_site_span = 8e3
tmon_coupling_pads_len = 100e3
h_jj = 200
w_jj = 100
asymmetry = 0.5

tmon = Tmon(claw.connections[1], tmon_cpw_params, tmon_arm_len, \
            tmon_JJ_arm_len, tmon_JJ_site_span, tmon_coupling_pads_len, \
            h_jj, w_jj, asymmetry, None)

tmon.place(canvas, region_name = "photo")
tmon.place(ebeam, region_name = "ebeam")

#qubit_ports.append(tmon.end)


#========= Flux coil drawing ============
fc_turn_radius = 240e3
coil_distance = 20e3
fc_segment_lengths =\
     [cp_fc.end.y - tmon.end.y - coil_distance]

fc = CPW_RL_Path(cp_fc.end, "L", fc_cpw_params, fc_turn_radius,
     fc_segment_lengths, [] ,trans_in = DTrans.R270)
fc.place(canvas)

fc_end = FluxCoil(fc.end, fc_cpw_params, width = 20e3, trans_in = DTrans.R180)
fc_end.place(canvas)


# ====== Microwave drives ========
md_turn_radius = 240e3
#md_distance = tmon_arm_len
md_distance = 20e3
md_segment_lengths =\
     [-200e3,\
     -(tmon.end.y - cp_md.end.y-tmon_JJ_arm_len - tmon_JJ_site_span - tmon_cpw_params.width/2),\
     -tmon.end.x + cp_md.end.x - 200e3 - tmon_arm_len - md_distance - tmon_cpw_params.width - \
                tmon_cpw_params.gap - 2*md_turn_radius]
#print(tmon.end)       
md = CPW_RL_Path(cp_md.end, "LRLRL", md_cpw_params, md_turn_radius,
     md_segment_lengths, [pi/2, -pi/2] ,trans_in = None)
md.place(canvas)

md_end = CPW(0, md_cpw_params.b/2, md.end, md.end + DPoint(4e3, 0))
md_end.place(canvas)





ebeam = ebeam.merge()
cell.shapes( layer_photo ).insert(canvas)
cell.shapes( layer_el ).insert(ebeam)



lv.zoom_fit()
