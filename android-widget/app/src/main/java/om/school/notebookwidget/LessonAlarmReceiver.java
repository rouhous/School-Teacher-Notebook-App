package om.school.notebookwidget;
import android.app.*;
import android.content.*;
import android.os.*;
public class LessonAlarmReceiver extends android.content.BroadcastReceiver {
 public static final String CHANNEL="teacher_lessons";
 @Override public void onReceive(Context c,Intent i){
  NotificationManager nm=(NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE);
  if(android.os.Build.VERSION.SDK_INT>=26)nm.createNotificationChannel(new NotificationChannel(CHANNEL,"تنبيهات الحصص",NotificationManager.IMPORTANCE_HIGH));
  Intent open=new Intent(c,MainActivity.class);
  android.app.PendingIntent pi=PendingIntent.getActivity(c,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  String title=i.getStringExtra("title");if(title==null)title="تنبيه الحصة";
  Notification.Builder b=android.os.Build.VERSION.SDK_INT>=26?new Notification.Builder(c,CHANNEL):new Notification.Builder(c);
  b.setContentTitle(title).setContentText("اضغط لفتح دفتر المعلم").setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
   .setContentIntent(pi).setAutoCancel(true).setCategory(Notification.CATEGORY_ALARM)
   .setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL)
   .setTimeoutAfter(20000).setVisibility(Notification.VISIBILITY_PRIVATE);
  nm.notify(i.getIntExtra("id",1),b.build());
 }
}
