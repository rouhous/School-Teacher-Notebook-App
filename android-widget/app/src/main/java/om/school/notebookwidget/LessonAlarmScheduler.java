package om.school.notebookwidget;
import android.app.*;
import android.content.*;
import android.os.Build;
import org.json.*;
import java.util.*;
import java.text.*;
public final class LessonAlarmScheduler {
 private LessonAlarmScheduler(){}
 public static void schedule(Context context,String snapshot){
  try{
   JSONObject root=new JSONObject(snapshot);
   JSONArray slots=root.getJSONArray("slots"),timing=root.getJSONArray("timing");
   AlarmManager manager=(AlarmManager)context.getSystemService(Context.ALARM_SERVICE);
   if(manager==null)return;
   Calendar now=Calendar.getInstance();
   for(int j=0;j<7;j++){
    Calendar day=(Calendar)now.clone();day.add(Calendar.DATE,j);
    int weekday=(day.get(Calendar.DAY_OF_WEEK)+6)%7; // Sunday=0, Monday=1, ... same as notebook schedule
    for(int k=0;k<slots.length();k++){
     JSONObject slot=slots.getJSONObject(k);
     int w=slot.optInt("weekday",-1),period=slot.optInt("period",-1);
     if(w!=weekday||period<1||period>8)continue;
     // Timings contain assembly and break entries; only lessons count as numbered periods.
     JSONObject t=null;int lesson=0;
     for(int ti=0;ti<timing.length();ti++){JSONObject x=timing.optJSONObject(ti);if(x==null)continue;
      String kind=x.optString("kind","lesson");if("assembly".equals(kind)||"break".equals(kind))continue;
      if(++lesson==period){t=x;break;}
     }
     if(t==null)continue;
     String start=t.optString("start",t.optString("from",""));
     String end=t.optString("end",t.optString("to",""));
     enqueue(context,manager,day,start,5,"بداية الحصة "+period,100000+j*1000+k*2);
     enqueue(context,manager,day,end,5,"نهاية الحصة "+period,100000+j*1000+k*2+1);
    }
   }
  }catch(Exception e){android.util.Log.w("LessonAlarm","Unable to schedule timetable",e);}
 }
 private static void enqueue(Context c,AlarmManager m,Calendar date,String time,int before,String title,int id){
  try{
   String[] x=time.trim().split(":");if(x.length<2)return;
   int h=Integer.parseInt(x[0]),minute=Integer.parseInt(x[1].replaceAll("[^0-9].*",""));
   if(h>23||minute>59)return;
   Calendar at=(Calendar)date.clone();at.set(Calendar.HOUR_OF_DAY,h);at.set(Calendar.MINUTE,minute);at.set(Calendar.SECOND,0);at.add(Calendar.MINUTE,-before);
   if(at.getTimeInMillis()<=System.currentTimeMillis())return;
   Intent intent=new Intent(c,LessonAlarmReceiver.class).putExtra("title",title).putExtra("id",id);
   PendingIntent pi=PendingIntent.getBroadcast(c,id,intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
   if(Build.VERSION.SDK_INT>=31&&!m.canScheduleExactAlarms())m.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,at.getTimeInMillis(),pi);
   else if(Build.VERSION.SDK_INT>=23)m.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,at.getTimeInMillis(),pi);
   else m.setExact(AlarmManager.RTC_WAKEUP,at.getTimeInMillis(),pi);
  }catch(Exception ignored){}
 }
}
