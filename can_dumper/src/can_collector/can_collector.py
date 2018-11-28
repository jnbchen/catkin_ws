#!/usr/bin/env python

import can, json, time, sched, can_parser, os
import rospy
from can_dumper.msg import *

class can_collector(object):
    def __init__(self):
        self.bus = []
        self.notifier = []
        self.listener = {}
        self.parser = {}
        self.radar_array_1 = RadarArray()
        self.radar_array_2 = RadarArray()
        self.radar_array_5 = RadarArray()
        self.radar_ = Radar()
        self.routelist = []
        self.buffer_ = []
        self.routeid = None
        self.topic_ = True
        self.pub_1 = rospy.Publisher('/can_dumper_node/can1_data', RadarArray, queue_size=1000)
        self.pub_2 = rospy.Publisher('/can_dumper_node/can2_data', RadarArray, queue_size=1000)
        self.pub_5 = rospy.Publisher('/can_dumper_node/can5_data', RadarArray, queue_size=1000)

        config             = rospy.get_param('~device_config_file', './')
        self.interval_     = rospy.get_param('~collect_interval', 10)
        self.broadcast_    = rospy.get_param('~broadcast_time', 50)

        with open(config, 'r') as f:
            record = json.load(f)
            if 'db_path' in record:
                db_dir = record['db_path'] + '/'
            else:
                db_dir = "./"
            if 'device' in record:
                for conf in record['device']:
                    channel = conf['channel']
                    self.parser[channel] = []
                    bus_filter = []
                    for fdb in conf['db']:
                        d = can_parser.can_parser(db_dir+fdb)
                        print(db_dir+fdb)
                        self.parser[channel].append(d)
                        filter_parser = d.get_filter(channel)
                        bus_filter += filter_parser

                    b = can.interface.Bus(bustype=conf['bustype'], channel=conf['channel'], bitrate=conf['bitrate'], can_filters=bus_filter)
                    self.bus.append(b)
                    l = can.BufferedReader()
                    n = can.Notifier(b, [l])
                    self.notifier.append(n)
                    self.listener[channel] = l
            if 'route_id' in record:
                self.routeid = record['route_id']

        self.job = sched.scheduler(time.time, time.sleep)

    def collect(self, args=None):
        self.job.enter(self.interval_/1000.0, 1, self.collect, argument=())
        for k, l in self.listener.items():
            qsize = l.buffer.qsize()
            for q in range(qsize):
                m = l.get_message(0)
                if m is not None:
                    for p in self.parser[k]:
                        r = p.decode(m)
                        if r is not None:
                           # if r['channel']=='can5':
                           #     print(r)
                            self.buffer_.append(r)
                            break

    def build_msg(self):
        buffer = {}
        for i in range(len(self.buffer_)):
            r = self.buffer_[i]
            radar = Radar()
            if (r['id'] == 0x60C or r['id'] == 0x61C) and r['channel'] == 'can1':
                device = str((r['id']&0x0F0)>>4)
                radar.id = r['Track_ID']
                radar.radar_type = 'ContiSSR208_' + device
                #print(radar.radar_type)
                radar.is_object = False
                radar.classification = 0xFF
                radar.distance_x = r['Track_LatDispl']
                radar.distance_y = r['Track_LongDispl']
                radar.relative_velocity_x = r['Track_VrelLat']
                radar.relative_velocity_y = r['Track_VrelLong']
                self.radar_array_1.header.stamp = rospy.get_rostime()
                self.radar_array_1.header.frame_id = 'radar'
                self.radar_array_1.radar_array.append(radar)
            elif (r['id'] == 0x62C or r['id'] == 0x63C) and r['channel'] == 'can2':
                device = str((r['id']&0x0F0)>>4)
                radar.id = r['Track_ID']
                radar.radar_type = 'ContiSSR208_' + device
                #print(radar.radar_type)
                radar.is_object = False
                radar.classification = 0xFF
                radar.distance_x = r['Track_LatDispl']
                radar.distance_y = r['Track_LongDispl']
                radar.relative_velocity_x = r['Track_VrelLat']
                radar.relative_velocity_y = r['Track_VrelLong']
                self.radar_array_2.header.stamp = rospy.get_rostime()
                self.radar_array_2.header.frame_id = 'radar'
                self.radar_array_2.radar_array.append(radar)
            elif (r['id'] == 0x60B or r['id'] == 0x60C or r['id'] == 0x60D) and r['channel'] == 'can5':
                id = r['Obj_ID']
                if id not in buffer.keys():
                    buffer[id] = r
                else:
                    buffer[radar.id].update(r)
                    radar.is_object = False
                    if len(buffer[radar.id].keys()) == 24:
                        radar.id = r['Obj_ID']
                        radar.radar_type = 'ContiARS408'
                        radar.is_object = True
                        radar.distance_x = r['Obj_DistLat']
                        radar.distance_y = r['Obj_DistLong']
                        radar.relative_velocity_x = r['Obj_VrelLat']
                        radar.relative_velocity_y = r['Obj_VrelLong']
                        radar.probolity_of_exist = r['Obj_ProbOfExist']
                        radar.classification = r['Obj_Class']
                        radar.measure_state = r['Obj_MeasState']
                        radar.object_size_x = r['Obj_Length']
                        radar.object_size_x = r['Obj_Width']
                        radar.angle = r['Obj_OrientationAngle']
                        radar.name = self.switch(radar.classification).get('name')
                        radar.r = self.switch(radar.classification).get('r')
                        radar.g = self.switch(radar.classification).get('g')
                        radar.b = self.switch(radar.classification).get('b')
                        radar.a = self.switch(radar.classification).get('a')
                        print(radar)

                        self.radar_array_5.header.stamp = rospy.get_rostime()
                        self.radar_array_5.header.frame_id = 'radar'
                        self.radar_array_5.radar_array.append(radar)

    def switch(self, var):
        return {
                self.radar_.POINT: {'name':'POINTS','r':1.0,'g':1.0,'b':1.0,'a':1.0},
                self.radar_.CAR: {'name':'CAR','r':0.0,'g':0.0,'b':1.0,'a':1.0},
                self.radar_.TRUCK: {'name':'TRUCK','r':1.0,'g':0.0,'b':1.0,'a':1.0},
                self.radar_.PEDESTRIAN: {'name':'PEDESTRIAN','r':1.0,'g':0.0,'b':0.0,'a':1.0},
                self.radar_.MOTORCYCLE: {'name':'MOTORCYCLE','r':0.0,'g':1.0,'b':1.0,'a':1.0},
                self.radar_.BICYCLE: {'name':'BICYCLE','r':1.0,'g':1.0,'b':0.0,'a':1.0},
                self.radar_.WIDE: {'name':'WIDE','r':1.0,'g':0.0,'b':1.0,'a':1.0}
        }.get(var,{'name':'UNKNOWN','r':1.0,'g':1.0,'b':1.0,'a':1.0})

    def broadcast(self, args=None):
        self.build_msg()
        #print(self.radar_array_)
        if self.topic_:
            self.pub_1.publish(self.radar_array_1)
            self.pub_2.publish(self.radar_array_2)
            self.pub_5.publish(self.radar_array_5)
            self.buffer_ = []
            self.radar_array_1.radar_array[:] = []
            self.radar_array_2.radar_array[:] = []
            self.radar_array_5.radar_array[:] = []
        self.job.enter(self.broadcast_/1000.0, 3, self.broadcast, argument=())

    def diagnostic(self, bus_id):
        if bus_id < 0 or bus_id >= len(self.bus):
            return -1

        curr = time.time()
        # hard-corded the name as can0-canxx, TBD
        k = "can" + str(bus_id)
        for p in self.parser[k]:
            if not p.lts.items():
                return 1
            # for the can message contain in dbc but have not received, the
            # last timestamp will not appear in the lts dictionary
            for mid, last in p.lts.items():
                # 3 seconds without any message with can id == mid received
                if (curr-last) > 3.0:
                    return mid
        return 0

    def start(self):
        self.job.enter(self.interval_/1000.0, 1, self.collect, argument=())
        self.job.enter(self.broadcast_/1000.0, 3, self.broadcast, argument=())
        self.job.run()
