package om.school.notebookwidget;
import android.app.Activity;
import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
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
  private FrameLayout notebookShell;
  private boolean deviceUnlocked=false;
  private boolean unlockPromptShown=false;
  private Button biometricLoginButton;
  private static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/";
  @Override public void onCreate(Bundle state){
    super.onCreate(state);
    boolean shared=getIntent()!=null && Intent.ACTION_SEND.equals(getIntent().getAction());
    if(shared)receiveSharedSchedule(getIntent());
    String cached=getSharedPreferences("widget",MODE_PRIVATE).getString("snapshot","");
    if(!cached.isEmpty())LessonAlarmScheduler.schedule(this,cached);
    getWindow().setStatusBarColor(0xFFF7FAF9);
    getWindow().setNavigationBarColor(0xFFF7FAF9);
    getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
    LinearLayout root=new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(28,40,28,28);
    root.setGravity(Gravity.CENTER);
    root.setBackgroundColor(0xFFF7FAF9);
    TextView title=new TextView(this);
    title.setText("ويدجت دفتر المعلم");
    title.setTextSize(26);
    title.setTextColor(0xFF075D4E);
    title.setGravity(Gravity.CENTER);
    root.addView(title);
    TextView info=new TextView(this);
    info.setText("الدفتر يعمل في متصفحك المعتاد، مع الاحتفاظ بالبصمة وإشعارات Web Push.\n\nهذا التطبيق مخصص للويدجت وتنبيهات Android المحلية. لتحديث الجدول افتح الدفتر واختر «إرسال الجدول إلى ويدجت Android» من قائمة المشاركة.");
    info.setTextSize(16);
    info.setPadding(0,28,0,28);
    info.setGravity(Gravity.CENTER);
    root.addView(info);
    Button open=new Button(this);
    open.setText("فتح دفتر المعلم في المتصفح");
    open.setOnClickListener(v->openNotebook());
    root.addView(open);
    Button sync=new Button(this);
    sync.setText("إرسال الجدول إلى الويدجيت (من الدفتر)");
    sync.setOnClickListener(v->{Toast.makeText(this,"افتح الدفتر، ثم اختر مشاركة الجدول إلى ويدجيت Android. الربط التلقائي الآمن قيد الإعداد.",Toast.LENGTH_LONG).show();openNotebook();});
    root.addView(sync);
    Button alertTest=new Button(this);
    alertTest.setText("اختبار تنبيه Android لمدة 20 ثانية");
    alertTest.setOnClickListener(v->{
      requestAndroidNotificationPermission();
      if(android.os.Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return;
      Intent i=new Intent(this,LessonAlertService.class).putExtra("title","اختبار تنبيه دفتر المعلم");
      try{if(Build.VERSION.SDK_INT>=26)startForegroundService(i);else startService(i);}
      catch(Exception e){Toast.makeText(this,"تعذر تشغيل التنبيه: "+e.getMessage(),Toast.LENGTH_LONG).show();}
    });
    root.addView(alertTest);
    Button flash=new Button(this);
    flash.setText("السماح بالفلاش (اختياري)");
    flash.setOnClickListener(v->requestOptionalFlashPermission());
    root.addView(flash);
    setContentView(root);
    // No embedded WebView: use the user's installed default browser for WebAuthn and Web Push.
    // Remain in the native widget companion; open the PWA only on explicit user action.
  }
  private void requestAndroidNotificationPermission(){
    // Native Android notification permission; this does not grant WebView Web Push support.
    if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
      requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1007);
    }
  }
  @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] results){
    super.onRequestPermissionsResult(requestCode,permissions,results);
    if(requestCode==1007 && (results.length==0||results[0]!=PackageManager.PERMISSION_GRANTED)){
      Toast.makeText(this,"يمكن السماح بإشعارات Android لاحقًا من إعدادات الهاتف",Toast.LENGTH_LONG).show();
    }
  }
  private void requestOptionalFlashPermission(){
    // The flash is optional: do not block lesson alarms if permission is denied.
    if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){
      new android.app.AlertDialog.Builder(this)
        .setTitle("فلاش التنبيه (اختياري)")
        .setMessage("هل تسمح باستخدام فلاش الكاميرا أثناء تنبيهات الحصص لمدة 20 ثانية؟ يمكن إبقاء الصوت والاهتزاز دون الفلاش.")
        .setPositiveButton("السماح",(dialog,which)->requestPermissions(new String[]{Manifest.permission.CAMERA},1009))
        .setNegativeButton("بدون فلاش",(dialog,which)->{})
        .show();
    }
  }
  private final Handler widgetHandler=new Handler(Looper.getMainLooper());
  private final Runnable widgetSyncLoop=new Runnable(){
    @Override public void run(){
      syncWidgetFromWeb();
      widgetHandler.postDelayed(this,60000);
    }
  };
  private void syncWidgetFromWeb(){
    if(notebookView==null || notebookView.getUrl()==null ||
      !notebookView.getUrl().startsWith(URL+"school-edition/school-notebook.html"))return;
    notebookView.evaluateJavascript("(function(){try{return JSON.stringify(window.schoolWidgetSnapshot?.()||null)}catch(e){return null}})()",value->{
      try{
        if(value==null||"null".equals(value))return;
        String payload=new org.json.JSONTokener(value).nextValue().toString();
        if("null".equals(payload)||payload.length()>100000)return;
        JSONObject data=new JSONObject(payload);
        JSONArray slots=data.getJSONArray("slots"),timing=data.getJSONArray("timing");
        if(slots.length()>500||timing.length()<8||timing.length()>20)return;
        String previous=getSharedPreferences("widget",MODE_PRIVATE).getString("snapshot","");
        if(!payload.equals(previous)){
          getSharedPreferences("widget",MODE_PRIVATE).edit().putString("snapshot",payload).apply();
          ScheduleWidget.refresh(this);
          WeeklyScheduleWidget.refresh(this);
          LessonAlarmScheduler.schedule(this,payload);
        }
      }catch(Exception ignored){}
    });
  }
  @Override protected void onResume(){
    super.onResume();
    widgetHandler.removeCallbacks(widgetSyncLoop);
    widgetHandler.postDelayed(widgetSyncLoop,3000);
  }
  @Override protected void onPause(){
    widgetHandler.removeCallbacks(widgetSyncLoop);
    super.onPause();
  }
  private void openEmbeddedNotebook(){
    notebookView=new WebView(this);
    notebookView.getSettings().setJavaScriptEnabled(true);
    notebookView.getSettings().setDomStorageEnabled(true);
    notebookView.getSettings().setAllowFileAccess(false);
    notebookView.getSettings().setAllowContentAccess(false);
    CookieManager.getInstance().setAcceptCookie(true);
    notebookView.setWebChromeClient(new WebChromeClient());
    notebookView.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
    notebookView.setFitsSystemWindows(false);
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
    notebookShell=shell;
    shell.setFitsSystemWindows(false);
    shell.addView(notebookView,new FrameLayout.LayoutParams(-1,-1));
    Button googleLogin=new Button(this);
    googleLogin.setText("الدخول الآمن بحساب Google");
    googleLogin.setTextColor(0xFFFFFFFF);
    googleLogin.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF1A73E8));
    FrameLayout.LayoutParams buttonParams=new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM);
    buttonParams.setMargins(24,0,24,72);
    shell.addView(googleLogin,buttonParams);
    Button browserFeatures=new Button(this);
    biometricLoginButton=browserFeatures;
    browserFeatures.setText("🔐 الدخول بالبصمة / Face ID");
    browserFeatures.setTextColor(0xFFFFFFFF);
    browserFeatures.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF075D4E));
    FrameLayout.LayoutParams browserParams=new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM);
    browserParams.setMargins(24,0,24,14);
    shell.addView(browserFeatures,browserParams);
    browserFeatures.setOnClickListener(v->promptNativeDeviceUnlock());
    browserFeatures.setVisibility(View.GONE);

    googleLogin.setVisibility(View.GONE);
    googleLogin.setOnClickListener(v->signInWithGoogle());
    notebookView.setWebViewClient(new WebViewClient(){
      @Override public void onPageFinished(WebView view,String url){
        boolean loginPage=url.equals(URL) || url.equals(URL+"index.html") || url.equals(URL+"#") || url.startsWith(URL+"index.html#");
        googleLogin.setVisibility(loginPage ? View.VISIBLE : View.GONE);
        browserFeatures.setVisibility(loginPage ? View.VISIBLE : View.GONE);
        if(!loginPage){
          getSharedPreferences("security",MODE_PRIVATE).edit().putBoolean("teacher_session_seen",true).apply();
          widgetHandler.postDelayed(()->syncWidgetFromWeb(),3500);
        }
        if(loginPage){
          view.evaluateJavascript("(function(){var x=document.getElementById('teacher-google');if(x)x.style.display='none';var b=document.getElementById('teacher-passkey-direct');if(b){b.disabled=true;b.style.display='none'}var p=document.getElementById('teacher-passkey-direct-status');if(p)p.textContent='';})()",null);
        }
      }
      @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
        Uri uri=request.getUrl();
        if("rouhous.github.io".equalsIgnoreCase(uri.getHost()))return false;
        openExternal(uri);return true;
      }
    });
    setContentView(shell);
    applySystemBars();
    notebookView.loadUrl(URL);
    // Show the welcome screen first. Re-entry biometric unlock is triggered after a verified teacher session.
  }
  private void promptNativeDeviceUnlock(){
    if(deviceUnlocked||unlockPromptShown||android.os.Build.VERSION.SDK_INT<28)return;
    if(!getSharedPreferences("security",MODE_PRIVATE).getBoolean("teacher_session_seen",false)){
      Toast.makeText(this,"سجّل دخولك بحساب Google أول مرة لربط البصمة بهذا الجهاز",Toast.LENGTH_LONG).show();return;
    }
    android.app.KeyguardManager km=(android.app.KeyguardManager)getSystemService(KEYGUARD_SERVICE);
    if(km==null||!km.isDeviceSecure())return;
    unlockPromptShown=true;
    if(notebookShell!=null)notebookShell.setVisibility(View.INVISIBLE);
    android.hardware.biometrics.BiometricPrompt prompt=new android.hardware.biometrics.BiometricPrompt.Builder(this)
      .setTitle("فتح دفتر المعلم")
      .setSubtitle("تحقق ببصمة الجهاز للمتابعة")
      .setNegativeButton("إلغاء",getMainExecutor(),(dialog,which)->{
        unlockPromptShown=false;
        if(notebookShell!=null)notebookShell.setVisibility(View.VISIBLE);
      }).build();
    prompt.authenticate(new CancellationSignal(),getMainExecutor(),new android.hardware.biometrics.BiometricPrompt.AuthenticationCallback(){
      @Override public void onAuthenticationSucceeded(android.hardware.biometrics.BiometricPrompt.AuthenticationResult result){
        deviceUnlocked=true;
        if(notebookShell!=null)notebookShell.setVisibility(View.VISIBLE);
        if(notebookView!=null&&notebookView.getUrl()!=null&&notebookView.getUrl().equals(URL))Toast.makeText(MainActivity.this,"تم فتح قفل الجهاز؛ يلزم استمرار جلسة Google للدخول إلى الدفتر",Toast.LENGTH_LONG).show();
      }
      @Override public void onAuthenticationError(int code,CharSequence message){
        unlockPromptShown=false;
        if(notebookShell!=null)notebookShell.setVisibility(View.VISIBLE);
        if(code==android.hardware.biometrics.BiometricPrompt.BIOMETRIC_ERROR_NO_BIOMETRICS||
           code==android.hardware.biometrics.BiometricPrompt.BIOMETRIC_ERROR_HW_UNAVAILABLE){
          // The phone may lack enrolled biometrics; fall back to its system lock screen.
          android.app.KeyguardManager manager=(android.app.KeyguardManager)getSystemService(KEYGUARD_SERVICE);
          if(manager!=null){
            Intent confirm=manager.createConfirmDeviceCredentialIntent("فتح دفتر المعلم","أدخل رمز قفل الجهاز");
            if(confirm!=null){startActivityForResult(confirm,1008);return;}
          }
        }
        Toast.makeText(MainActivity.this,"لم يتم فتح التطبيق: "+message,Toast.LENGTH_LONG).show();
      }
    });
  }
  @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
    super.onActivityResult(requestCode,resultCode,data);
    if(requestCode==1008&&resultCode==RESULT_OK){
      deviceUnlocked=true;
      if(notebookShell!=null)notebookShell.setVisibility(View.VISIBLE);
    }
  }
  private void applySystemBars(){
    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN|WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
    getWindow().setStatusBarColor(0xFFF7FAF9);
    getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
    if(notebookShell==null)return;
    // Android 15 forces edge-to-edge. Inset the native container, not the web document:
    // WebView.setPadding can leave the page's header under the status icons.
    notebookShell.setOnApplyWindowInsetsListener((view,insets)->{
      android.graphics.Insets bars;
      if(android.os.Build.VERSION.SDK_INT>=30){
        bars=insets.getInsets(android.view.WindowInsets.Type.statusBars()|android.view.WindowInsets.Type.navigationBars());
        view.setPadding(0,bars.top,0,bars.bottom);
      }else{
        view.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());
      }
      return insets;
    });
    notebookShell.requestApplyInsets();
  }
  @Override public void onWindowFocusChanged(boolean hasFocus){
    super.onWindowFocusChanged(hasFocus);
    if(hasFocus)applySystemBars();
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
              // Do not mark login successful until the authenticated teacher page actually loads.
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
      Intent browser=new Intent(Intent.ACTION_VIEW,Uri.parse(URL));
      browser.addCategory(Intent.CATEGORY_BROWSABLE);
      startActivity(browser);
    }catch(Exception e){
      Toast.makeText(this,"ثبّت متصفح Firefox أو Chrome لفتح دفتر المعلم",Toast.LENGTH_LONG).show();
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
      WeeklyScheduleWidget.refresh(this);
      LessonAlarmScheduler.schedule(this,data.toString());
      Toast.makeText(this,"تم تحديث ويدجت الجدول بنجاح",Toast.LENGTH_LONG).show();
    }catch(Exception e){
      Toast.makeText(this,"تعذر استيراد الجدول. استخدم زر المشاركة من دفتر المعلم.",Toast.LENGTH_LONG).show();
    }
  }
}
