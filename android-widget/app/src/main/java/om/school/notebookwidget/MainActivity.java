package om.school.notebookwidget;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Toast;
import android.content.Intent;
import android.net.Uri;
import org.json.JSONObject;
import org.json.JSONTokener;

public class MainActivity extends Activity {
  private WebView web;
  private static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/school-edition/school-notebook.html";
  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
    Button sync=new Button(this);sync.setText("تحديث ويدجت الجدول");
    web=new WebView(this);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.setWebViewClient(new WebViewClient(){
      @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request){
        Uri uri=request.getUrl();
        if("rouhous.github.io".equals(uri.getHost()) && "https".equals(uri.getScheme()))return false;
        try{startActivity(new Intent(Intent.ACTION_VIEW,uri));}catch(Exception ignored){}
        return true;
      }
    });
    sync.setOnClickListener(v->syncSnapshot());
    root.addView(sync);root.addView(web,new LinearLayout.LayoutParams(-1,0,1));
    setContentView(root);web.loadUrl(URL);
  }
  private void syncSnapshot(){
    web.evaluateJavascript("(function(){return JSON.stringify(window.schoolWidgetSnapshot?window.schoolWidgetSnapshot():null)})()",raw->{
      try{
        String decoded=(String)new JSONTokener(raw).nextValue();
        JSONObject data=new JSONObject(decoded);
        if(data.optJSONArray("slots")==null||data.optJSONArray("timing")==null)throw new Exception();
        getSharedPreferences("widget",MODE_PRIVATE).edit().putString("snapshot",data.toString()).apply();
        ScheduleWidget.refresh(this);
        Toast.makeText(this,"تم تحديث الجدول",Toast.LENGTH_SHORT).show();
      }catch(Exception e){Toast.makeText(this,"سجل الدخول وانتظر تحميل الجدول المعتمد",Toast.LENGTH_LONG).show();}
    });
  }
  @Override protected void onDestroy(){if(web!=null)web.destroy();super.onDestroy();}
}
