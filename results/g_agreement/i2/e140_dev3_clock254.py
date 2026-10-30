"""Creation-clock accounting only; no IO/model/selection/scientific operations."""
import math
SEEDS={'base':300.,'generation_cold':36.60640698100906,'generation_post':7.009325373917818,'capture':31.899021986988373,'oracle_setup':200.,'native':42.71863326104358,'mac_roundtrip':180.}
def forecast(elapsed,remaining,maxima,cap):
 if not(math.isfinite(elapsed)and elapsed>=0 and 0<cap<=9300):raise ValueError('original clock/cap')
 if any(type(n)is not int or n<0 for n in remaining.values()):raise ValueError('remaining phase counts')
 if any(n and(k not in maxima or not math.isfinite(maxima[k])or maxima[k]<=0)for k,n in remaining.items()):raise ValueError('every pending phase needs retained measured/bounded maximum')
 need=1.25*(elapsed+sum(n*maxima[k]for k,n in remaining.items()if n))+60
 return {'status':'ADMIT'if need<=cap else'NO_FIT','projected_total_cap_seconds':need,'elapsed_from_creation':elapsed,'remaining':remaining,'maxima':maxima.copy(),'margin':1.25,'reserve_seconds':60}
def initial(screen_batches=85,main_batches=36):
 if screen_batches!=85 or main_batches!=36:raise ValueError('exact frozen grouped-census bound')
 return forecast(248,{'base':1,'generation_cold':1,'generation_post':screen_batches-1,'capture':main_batches,'oracle_setup':1,'native':3*main_batches,'mac_roundtrip':1},SEEDS,9300)
def screen_remaining(batches,index,main_batches=36):
 if not(0<=index<batches and batches==85 and main_batches==36):raise ValueError('exact screen counter')
 return {'generation_cold':int(index==0),'generation_post':batches-index-int(index==0),'capture':main_batches,'oracle_setup':1,'native':3*main_batches,'mac_roundtrip':1}
def main_remaining(batches,index):
 if not(10<=batches<=36 and 0<=index<=4*batches):raise ValueError('main counter')
 if index<batches:return {'capture':batches-index,'oracle_setup':1,'native':3*batches}
 if index==batches:return {'capture':0,'oracle_setup':1,'native':3*batches}
 return {'capture':0,'oracle_setup':0,'native':4*batches-index+1}
def retain(maxima,phase,seconds):
 if not(math.isfinite(seconds)and seconds>0):raise ValueError('measured phase duration')
 maxima[phase]=max(maxima.get(phase,0),seconds)
