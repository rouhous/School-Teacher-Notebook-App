package om.school.notebookwidget;
import android.content.*;
import android.os.Build;
public class LessonAlarmReceiver extends BroadcastReceiver {
 @Override public void onReceive(Context context,Intent intent){
  // Update highlighted timetable rows whenever a lesson alarm arrives.
  ScheduleWidget.refresh(context);
  WeeklyScheduleWidget.refresh(context);
  Intent service=new Intent(context,LessonAlertService.class);
  service.putExtra("title",intent==null?"تنبيه الحصة":intent.getStringExtra("title"));
  try{
   if(Build.VERSION.SDK_INT>=26)context.startForegroundService(service);
   else context.startService(service);
  }catch(Exception e){android.util.Log.e("LessonAlarm","Unable to launch alert service",e);}
 }
}
