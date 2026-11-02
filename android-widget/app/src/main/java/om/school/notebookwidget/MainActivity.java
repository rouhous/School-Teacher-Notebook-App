package om.school.notebookwidget;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.view.Gravity;
import android.widget.Toast;
import androidx.browser.customtabs.CustomTabsIntent;
import org.json.JSONObject;
import org.json.JSONArray;

/**
 * Pilot launcher: use the system browser for Google authentication.
 * Embedded WebView and the external browser do not share a login session.
 * Never claim that a browser login has synchronized the widget.
 */
public class MainActivity extends Activity {
  private static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/";
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    receiveSharedSchedule(getIntent());
    LinearLayout root=new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(28,48,28,28);
    root.setGravity(Gravity.CENTER);
    root.setBackgroundColor(0xFFE9F5EF);
    TextView title=new TextView(this);
    title.setText("دفتر المعلم المدرسي");
    title.setTextSize(26);
    title.setTextColor(0xFF075D4E);
    title.setGravity(Gravity.CENTER);
    root.addView(title);
    TextView info=new TextView(this);
    info.setText("الدفتر الكامل: الجداول، الطلاب، الحضور، التقييم والتقارير.\nتسجيل Google يتم بأمان داخل متصفح موثوق مع الاحتفاظ بجلسة الدخول.\n\nلمزامنة الويدجت: افتح الجدول واضغط «إرسال الجدول إلى ويدجت Android» ثم اختر دفتر المعلم من المشاركة.");
    info.setTextSize(17);
    info.setPadding(0,32,0,32);
    info.setGravity(Gravity.CENTER);
    root.addView(info);
    Button open=new Button(this);
    open.setText("فتح دفتر المعلم الكامل");
    open.setOnClickListener(v->openNotebook());
    root.addView(open);
    setContentView(root);
  }
  private void openNotebook(){
    try{
      CustomTabsIntent tab=new CustomTabsIntent.Builder()
          .setShowTitle(false)
          .setToolbarColor(0xFF075D4E)
          .build();
      tab.launchUrl(this,Uri.parse(URL));
    }catch(Exception e){
      startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(URL)));
    }
  }
  @Override protected void onNewIntent(Intent intent){
    super.onNewIntent(intent);
    setIntent(intent);
    receiveSharedSchedule(intent);
  }
  private void receiveSharedSchedule(Intent intent){
    if(intent==null || !Intent.ACTION_SEND.equals(intent.getAction()))return;
    String raw=intent.getStringExtra(Intent.EXTRA_TEXT);
    try{
      if(raw==null || !raw.startsWith("SCHOOL_WIDGET_V1:"))throw new Exception("Not a timetable");
      String payload=raw.substring("SCHOOL_WIDGET_V1:".length());
      if(payload.length()>100000)throw new Exception("Oversized");
      JSONObject data=new JSONObject(payload);
      JSONArray slots=data.getJSONArray("slots");
      JSONArray timing=data.getJSONArray("timing");
      if(slots.length()>500 || timing.length()>20 || timing.length()<8)throw new Exception("Invalid size");
      for(int i=0;i<slots.length();i++){
        JSONObject slot=slots.getJSONObject(i);
        if(!slot.has("weekday") || !slot.has("period"))throw new Exception("Invalid slot");
      }
      getSharedPreferences("widget",MODE_PRIVATE).edit().putString("snapshot",data.toString()).apply();
      ScheduleWidget.refresh(this);
      Toast.makeText(this,"تم تحديث ويدجت الجدول بنجاح",Toast.LENGTH_LONG).show();
    }catch(Exception e){
      Toast.makeText(this,"تعذر استيراد الجدول. استخدم زر المشاركة من دفتر المعلم.",Toast.LENGTH_LONG).show();
    }
  }
}
