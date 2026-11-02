package om.school.notebookwidget;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.view.Gravity;

/**
 * Pilot launcher: use the system browser for Google authentication.
 * Embedded WebView and the external browser do not share a login session.
 * Never claim that a browser login has synchronized the widget.
 */
public class MainActivity extends Activity {
  private static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/";
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
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
    info.setText("افتح الدفتر في المتصفح لتسجيل الدخول بحساب Google بأمان.\n\nالويدجت موجود في قائمة أدوات الشاشة، لكن ربطه بالجدول الحقيقي لم يكتمل بعد في هذه النسخة التجريبية.");
    info.setTextSize(17);
    info.setPadding(0,32,0,32);
    info.setGravity(Gravity.CENTER);
    root.addView(info);
    Button open=new Button(this);
    open.setText("فتح دفتر المعلم في المتصفح");
    open.setOnClickListener(v->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(URL))));
    root.addView(open);
    setContentView(root);
  }
}
