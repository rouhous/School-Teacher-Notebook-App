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
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.CookieManager;
import org.json.JSONObject;
import androidx.credentials.CredentialManager;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.exceptions.GetCredentialException;
import androidx.credentials.CustomCredential;
import com.google.android.libraries.identity.googleid.GetGoogleIdOption;
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import androidx.credentials.exceptions.NoCredentialException;
import androidx.credentials.exceptions.GetCredentialCancellationException;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;
import android.os.CancellationSignal;
import android.widget.FrameLayout;
import android.view.ViewGroup;
import android.view.View;
import android.view.WindowManager;
import android.graphics.Color;
import org.json.JSONArray;

/**
 * Pilot launcher: use the system browser for Google authentication.
 * Embedded WebView and the external browser do not share a login session.
 * Never claim that a browser login has synchronized the widget.
 */
public class MainActivity extends Activity {
  private WebView notebookView;
  private static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/";
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    receiveSharedSchedule(getIntent());
    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
    getWindow().setStatusBarColor(0xFF075D4E);
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
    getWindow().getDecorView().setSystemUiVisibility(0);
    getWindow().setNavigationBarColor(0xFF075D4E);
    getWindow().getDecorView().setSystemUiVisibility(0);
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
    openEmbeddedNotebook();
  }
  private void openEmbeddedNotebook(){
    notebookView=new WebView(this);
    notebookView.getSettings().setJavaScriptEnabled(true);
    notebookView.getSettings().setDomStorageEnabled(true);
    notebookView.getSettings().setAllowFileAccess(false);
    notebookView.getSettings().setAllowContentAccess(false);
    CookieManager.getInstance().setAcceptCookie(true);
    notebookView.setWebChromeClient(new WebChromeClient());
    notebookView.setSystemUiVisibility(0);
    notebookView.setFitsSystemWindows(true);
    notebookView.setWebViewClient(new WebViewClient(){
      @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
        Uri uri=request.getUrl();
        String host=uri.getHost()==null?"":uri.getHost().toLowerCase(java.util.Locale.ROOT);
        if(host.equals("rouhous.github.io"))return false;
        // OAuth providers should never authenticate inside an embedded WebView.
        openExternal(uri);
        return true;
      }
    });
    FrameLayout shell=new FrameLayout(this);
    shell.setFitsSystemWindows(true);
    shell.addView(notebookView,new FrameLayout.LayoutParams(-1,-1));
    Button googleLogin=new Button(this);
    googleLogin.setText("الدخول الآمن بحساب Google");
    googleLogin.setTextColor(0xFFFFFFFF);
    googleLogin.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF075D4E));
    FrameLayout.LayoutParams buttonParams=new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM);
    buttonParams.setMargins(24,0,24,24);
    shell.addView(googleLogin,buttonParams);
    googleLogin.setVisibility(View.GONE);
    googleLogin.setOnClickListener(v->signInWithGoogle());
    notebookView.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView view,String url){
        boolean loginPage=url.equals(URL) || url.equals(URL+"index.html") || url.equals(URL+"#") || url.startsWith(URL+"index.html#");
        googleLogin.setVisibility(loginPage ? View.VISIBLE : View.GONE);
        if(loginPage){
          view.evaluateJavascript("(function(){var x=document.getElementById('teacher-google');if(x)x.style.display='none';})()",null);
        }
      }
      @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
        Uri uri=request.getUrl();
        if("rouhous.github.io".equalsIgnoreCase(uri.getHost()))return false;
        openExternal(uri);return true;
      }
    });
    setContentView(shell);
    notebookView.loadUrl(URL);
  }
  private void signInWithGoogle(){
    GetGoogleIdOption googleOption=new GetGoogleIdOption.Builder()
      .setServerClientId("825380653679-u542mtddqblq5nrt0pctj8sbfe9sg4dj.apps.googleusercontent.com")
      .setFilterByAuthorizedAccounts(false)
      .build();
    GetCredentialRequest request=new GetCredentialRequest.Builder().addCredentialOption(googleOption).build();
    requestGoogleCredential(request,true);
  }
  private void requestGoogleCredential(GetCredentialRequest request,boolean allowFallback){
    CredentialManager.create(this).getCredentialAsync(this,request,new CancellationSignal(),
      getMainExecutor(),new CredentialManagerCallback<GetCredentialResponse,GetCredentialException>(){
        @Override public void onResult(GetCredentialResponse response){
          if(!(response.getCredential() instanceof CustomCredential)){
            Toast.makeText(MainActivity.this,"نوع تسجيل الدخول غير مدعوم",Toast.LENGTH_LONG).show();return;
          }
          CustomCredential credential=(CustomCredential)response.getCredential();
          if(!GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(credential.getType()))return;
          try{
            String token=GoogleIdTokenCredential.createFrom(credential.getData()).getIdToken();
            String quoted=JSONObject.quote(token);
            if(notebookView!=null && notebookView.getUrl()!=null &&
               notebookView.getUrl().startsWith(URL)){
              notebookView.evaluateJavascript(
                "window.schoolNotebookNativeGoogleSignIn && window.schoolNotebookNativeGoogleSignIn("+quoted+")",null);
            }
          }catch(Exception ex){Toast.makeText(MainActivity.this,"تعذر قراءة تسجيل Google",Toast.LENGTH_LONG).show();}
        }
        @Override public void onError(GetCredentialException error){
          if(allowFallback && error instanceof NoCredentialException){
            GetSignInWithGoogleOption explicit=new GetSignInWithGoogleOption.Builder(
              "825380653679-u542mtddqblq5nrt0pctj8sbfe9sg4dj.apps.googleusercontent.com").build();
            requestGoogleCredential(new GetCredentialRequest.Builder().addCredentialOption(explicit).build(),false);
            return;
          }
          if(error instanceof GetCredentialCancellationException){
            Toast.makeText(MainActivity.this,"لم يكتمل اختيار حساب Google. حاول مرة أخرى.",Toast.LENGTH_LONG).show();
            return;
          }
          Toast.makeText(MainActivity.this,"تعذر تسجيل Google: "+error.getClass().getSimpleName()+". تحقق من تحديث خدمات Google Play.",Toast.LENGTH_LONG).show();
        }
      });
  }
  private void openExternal(Uri uri){
    try{
      CustomTabsIntent tab=new CustomTabsIntent.Builder().setToolbarColor(0xFF075D4E).build();
      tab.launchUrl(this,uri);
    }catch(Exception e){startActivity(new Intent(Intent.ACTION_VIEW,uri));}
  }
  @Override public void onBackPressed(){
    if(notebookView!=null && notebookView.canGoBack())notebookView.goBack();
    else super.onBackPressed();
  }
  @Override protected void onDestroy(){
    if(notebookView!=null){notebookView.destroy();notebookView=null;}
    super.onDestroy();
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
