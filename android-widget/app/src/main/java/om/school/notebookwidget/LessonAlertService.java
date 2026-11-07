package om.school.notebookwidget;
import android.app.*;
import android.content.*;
import android.hardware.camera2.*;
import android.media.*;
import android.os.*;
public class LessonAlertService extends Service {
 public static final String CHANNEL="teacher_alerts_20s";
 private final Handler handler=new Handler(Looper.getMainLooper());
 private Ringtone tone;
 private Vibrator vibrator;
 private CameraManager cameras;
 private String torchId;
 private boolean torchOn=false;
 private final Runnable stop=()->stopSelf();
 private final Runnable blink=new Runnable(){
  @Override public void run(){
   try{if(cameras!=null&&torchId!=null){torchOn=!torchOn;cameras.setTorchMode(torchId,torchOn);}}catch(Exception ignored){}
   handler.postDelayed(this,650);
  }
 };
 @Override public void onCreate(){
  super.onCreate();
  NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
  NotificationChannel channel=new NotificationChannel(CHANNEL,"تنبيه صوتي للحصص (20 ثانية)",NotificationManager.IMPORTANCE_HIGH);
  channel.enableVibration(true);
  channel.setVibrationPattern(new long[]{0,500,300,500,300,500});
  nm.createNotificationChannel(channel);
 }
 @Override public int onStartCommand(Intent intent,int flags,int startId){
  if(intent!=null&&"STOP".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
  String title=intent==null?"تنبيه الحصة":intent.getStringExtra("title");
  if(title==null||title.isEmpty())title="تنبيه الحصة";
  Intent stopIntent=new Intent(this,LessonAlertService.class).setAction("STOP");
  PendingIntent stopPi=PendingIntent.getService(this,2001,stopIntent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  PendingIntent openPi=PendingIntent.getActivity(this,2002,new Intent(this,MainActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  Notification n=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
   .setContentTitle(title).setContentText("التنبيه يعمل لمدة 20 ثانية").setContentIntent(openPi)
   .addAction(new Notification.Action.Builder(android.R.drawable.ic_media_pause,"إيقاف التنبيه",stopPi).build())
   .setOngoing(true).setCategory(Notification.CATEGORY_ALARM).build();
  if(Build.VERSION.SDK_INT>=29)startForeground(2003,n,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
  else startForeground(2003,n);
  try{
   android.net.Uri uri=RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
   if(uri==null)uri=RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
   tone=RingtoneManager.getRingtone(this,uri);
   if(tone!=null){if(Build.VERSION.SDK_INT>=28)tone.setLooping(true);tone.play();}
  }catch(Exception ignored){}
  try{
   vibrator=(Vibrator)getSystemService(VIBRATOR_SERVICE);
   if(vibrator!=null&&vibrator.hasVibrator())vibrator.vibrate(VibrationEffect.createWaveform(new long[]{0,500,300,500,300,500},0));
  }catch(Exception ignored){}
  // Camera flash is optional and only enabled if the user granted CAMERA permission.
  if(checkSelfPermission(android.Manifest.permission.CAMERA)==android.content.pm.PackageManager.PERMISSION_GRANTED){
   try{
    cameras=(CameraManager)getSystemService(CAMERA_SERVICE);
    for(String id:cameras.getCameraIdList()){
     android.hardware.camera2.CameraCharacteristics cc=cameras.getCameraCharacteristics(id);
     if(Boolean.TRUE.equals(cc.get(android.hardware.camera2.CameraCharacteristics.FLASH_INFO_AVAILABLE))){torchId=id;break;}
    }
    if(torchId!=null)handler.post(blink);
   }catch(Exception ignored){}
  }
  handler.removeCallbacks(stop);handler.postDelayed(stop,20000);
  return START_NOT_STICKY;
 }
 @Override public void onDestroy(){
  handler.removeCallbacksAndMessages(null);
  try{if(tone!=null)tone.stop();}catch(Exception ignored){}
  try{if(vibrator!=null)vibrator.cancel();}catch(Exception ignored){}
  try{if(cameras!=null&&torchId!=null)cameras.setTorchMode(torchId,false);}catch(Exception ignored){}
  super.onDestroy();
 }
 @Override public IBinder onBind(Intent i){return null;}
}
