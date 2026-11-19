"""
tools/ticker.py   (Nov 19) The walk's street ticker: what the block does tonight, written for a person, not a log file.

MLow, Nov 19: "the moving text is kind of nonsense make it make more sense and be funny". block.json's log is the
machine record (every window light by apartment code). This is the same night, hand written: one line per thing you
could actually see, each at the minute it happens in the scene, plus a running count of lit windows written as a
sentence. Writes walk/assets/ticker.json, which walk.js and pano.js read before block.json's log.

  python3 tools/ticker.py SITE_ASSETS_DIR
"""
import json, os, sys

def T(s):
    h, m = s.split(':'); return int(h) * 60 + int(m)

LINES = [
    ('00:09', "Somebody on the stoop of 309 comes out to find the saxophone. Finds it. Goes back in."),
    ('00:11', "Two smokers outside LAST CALL. One is telling the long version. The other has heard it."),
    ('00:28', "The DJ leaves 335 with two record bags. Nobody asked, but it was a great set."),
    ('00:44', "The Night Shift comes up out of the subway. Their day is over. It is 12:44 a.m."),
    ('00:50', "A man on the stoop of 312 says yes, no, yes into a phone. The phone is winning."),
    ('01:02', "SOFT WATER LAUNDROMAT turns the lights down. Your socks are still in dryer six."),
    ('01:11', "A cab drops someone at 304 and waits until the door shuts. Manners, at 1 a.m."),
    ('01:20', "The Night Owls are up. Eight windows lit for no reason anyone will admit to."),
    ('01:26', "The New Parents are awake. They were also awake at 11:40, and at 12:55."),
    ('01:41', "A delivery bike idles outside LATE SLICE. The pizza is for 6B. 6B is asleep."),
    ('02:05', "The Rat crosses from the garden to the trash at LATE SLICE. Nobody sees. The Rat prefers it."),
    ('02:12', "It starts to rain. Every awning on the block becomes a gutter."),
    ('02:21', "An umbrella goes by fast, east to west. The person under it has somewhere to be."),
    ('02:25', "The Insomniac turns on a light. Then another. Then reads the whole lease."),
    ('02:29', "A second umbrella gives up and waits under the scaffold at The Meridian Arms."),
    ('02:55', "The Baker's alarm goes off. The Baker was already awake."),
    ('03:04', "The rain stops. The street keeps it, mostly in the potholes."),
    ('03:11', "The Baker walks eleven steps to work. The best commute in New York."),
    ('03:17', "The Bodega Cat leaves the window of BLUE EYE GROCERY, crosses without looking, sits on the garden wall. Traffic waits. There is no traffic."),
    ('03:18', "FIRST LIGHT BAKERY: lights on. The block will smell like bread in forty minutes."),
    ('03:27', "The DJ gets home and turns on every light like a set is starting."),
    ('03:56', "LAST CALL turns the lights all the way up. This is the worst moment of everyone's night."),
    ('04:08', "Two people leave LAST CALL and argue about which way the train is. Both are wrong."),
    ('04:18', "The Cab Driver walks to the avenue to start a shift. The bar crowd walks to the avenue to end one."),
    ('04:19', "The Pizza Man pulls the gate at LATE SLICE, lights a cigarette, walks east. Day done."),
    ('04:22', "The Bartender pulls the gate at LAST CALL, checks it twice, goes upstairs. Checks it once more from the window."),
    ('04:23', "The Bodega Cat walks back. The door is propped. Breakfast."),
    ('04:28', "The flour truck backs up to FIRST LIGHT BAKERY. Twelve sacks. Beep. Beep. Beep. Beep."),
    ('04:41', "The Line Cook opens CLOUD DINER and the grill goes on. The eggs have no idea."),
    ('04:56', "The newspaper van throws three bundles at BLUE EYE GROCERY without stopping. Perfect aim. No witnesses."),
    ('05:10', "The flower van double parks at PETAL & STEM. Buckets, boxes and one small tree, at 5 a.m."),
    ('05:15', "The Super carries fourteen bags up from the cellar and builds the pile at the kerb. It is architecture."),
    ('05:20', "The kitchens wake up. Every window that was a TV is now a kettle."),
    ('05:27', "A car pulls out on the south side. The spot is gone in four minutes. That is a slow day."),
    ('05:35', "The garbage truck works the block west. Brakes, hopper, brakes. The whole street hears it and pretends not to."),
    ('05:38', "Eleven windows at once. Somebody's alarm is set for the whole building."),
    ('05:45', "SOFT WATER LAUNDROMAT opens. Dryer six is still running."),
    ('05:52', "The Runner leaves Halcyon Court, checks a watch, goes west. Someone with a suitcase waits for a car to the airport. It comes. Miracle."),
    ('05:56', "The Nurse leaves for the 7 o'clock handover. The only person on the block who knows what time it really is."),
    ('06:00', "FIRST LIGHT BAKERY opens the gate. The line has opinions already."),
    ('06:17', "First grey in the east. The sky is a colour again."),
    ('06:21', "The Line Cook stands outside CLOUD DINER for exactly one cigarette. Timed it."),
    ('06:32', "The Dog Walker comes by with three dogs. One of them is in charge, and it is not the Dog Walker."),
    ('06:34', "All six street lights go off at once, like they rehearsed."),
    ('06:40', "School morning. Somebody upstairs cannot find a shoe."),
    ('06:46', "Sunrise, somewhere behind the avenue. The line at FIRST LIGHT is four deep."),
    ('07:00', "The Super hoses the sidewalk east to west, the way it has always been done. Do not ask about west to east."),
    ('07:08', "The Runner comes back the other way, slower. Different face."),
    ('07:13', "The sun lines up with the street and comes straight down it. Twice a year this is a tourist event. Today it is just Wednesday."),
    ('07:16', "The Mechanic rolls both gates up at 317 FLAT FIX and drags out the tire rack. Nobody has a flat. Yet."),
    ('07:26', "Four kids wait for the bus outside Halcyon Court. One has forgotten something. You can tell."),
    ('07:30', "The bakery line is nine deep. Two of them came out for milk."),
    ('07:32', "The street sweeper comes through with its brushes down. Two cars did not move. Two tickets."),
    ('07:38', "The school bus stops at Halcyon Court. Lights flash. Four kids get on. One runs back."),
    ('07:42', "The Pharmacist opens CORNER RX with a coffee from the diner. The block is officially awake."),
    ('08:00', "Eight o'clock. The shift is over. Nobody was in charge, and it went fine."),
]

def lit_windows(block, t):
    n = 0
    for w in block['windows']:
        for a, b, kind in w.get('s', []):
            if a <= t < b: n += 1; break
    return n

if __name__ == '__main__':
    out = sys.argv[1]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lines = [[T(a), s] for a, s in LINES]
    for _, s in lines:
        assert '—' not in s and '–' not in s, s
    lines.sort(key=lambda x: x[0])
    json.dump({'lines': lines}, open(os.path.join(out, 'ticker.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    print('ticker', len(lines), 'lines')
