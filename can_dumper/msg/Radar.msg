uint8 POINT=0
uint8 CAR=1
uint8 TRUCK=2
uint8 PEDESTRIAN=3
uint8 MOTORCYCLE=4
uint8 BICYCLE=5
uint8 WIDE=6

uint32 id
uint8 classification
uint8 roll_count

string radar_type
bool is_object

uint8 measure_state
uint8 probolity_of_exist

float32 rcs_value

geometry_msgs/Pose2D pose

float32 relative_velocity_x
float32 relative_velocity_y

float32 object_size_x
float32 object_size_y

float32 lifetime

string  name
std_msgs/ColorRGBA color



