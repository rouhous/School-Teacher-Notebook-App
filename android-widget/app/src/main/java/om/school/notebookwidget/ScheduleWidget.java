package om.school.notebookwidget;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;
import org.json.JSONArray;
import org.json.JSONObject;
import java.time.LocalDate;
import java.util.Locale;
import java.time.LocalTime;
import android.text.SpannableString;
import android.text.SpannableStringBuilder;
import android.text.style.ForegroundColorSpan;
import android.text.style.StyleSpan;
import android.graphics.Typeface;
import android.text.Spanned;

public class ScheduleWidget extends AppWidgetProvider {
  public static void refresh(Context ctx){
    AppWidgetManager manager=AppWidgetManager.getInstance(ctx);
    ComponentName name=new ComponentName(ctx,ScheduleWidget.class);
    int[] ids=manager.getAppWidgetIds(name);
    for(int id:ids)render(ctx,manager,id);
  }
  @Override public void onUpdate(Context ctx,AppWidgetManager mgr,int[] ids){
    for(int id:ids)render(ctx,mgr,id);
  }
  private static void render(Context ctx,AppWidgetManager mgr,int id){
    RemoteViews view=new RemoteViews(ctx.getPackageName(),R.layout.widget_schedule);
    view.setTextViewText(R.id.widget_content,buildText(ctx));
    view.setTextViewText(R.id.widget_date,LocalDate.now().toString());
    view.setTextViewText(R.id.widget_current,currentPeriod(ctx));
    Intent intent=new Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://rouhous.github.io/School-Teacher-Notebook-App/"));
    PendingIntent open=PendingIntent.getActivity(ctx,0,intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    view.setOnClickPendingIntent(R.id.widget_content,open);
    view.setOnClickPendingIntent(R.id.widget_title,open);
    view.setOnClickPendingIntent(R.id.widget_current,open);
    mgr.updateAppWidget(id,view);
  }
  private static String currentPeriod(Context ctx){
    try{
      String json=ctx.getSharedPreferences("widget",Context.MODE_PRIVATE).getString("snapshot",null);
      if(json==null)return "أرسل الجدول من دفتر المعلم لتفعيل الويدجت";
      JSONObject data=new JSONObject(json);
      JSONArray timing=data.getJSONArray("timing");
      JSONArray slots=data.getJSONArray("slots");
      JSONArray cover=data.optJSONArray("cover");
      LocalTime now=LocalTime.now();
      int weekday=(LocalDate.now().getDayOfWeek().getValue()%7)+1;
      if(weekday>5)return "عطلة نهاية الأسبوع";
      int number=0;
      for(int i=0;i<timing.length();i++){
        JSONObject t=timing.getJSONObject(i);
        String kind=t.optString("kind","lesson");
        if(!"assembly".equals(kind)&&!"break".equals(kind))number++;
        try{
          LocalTime from=LocalTime.parse(t.optString("start"));
          LocalTime until=LocalTime.parse(t.optString("end"));
          if(now.isBefore(from)||!now.isBefore(until))continue;
          if("assembly".equals(kind))return "الآن: الطابور الصباحي";
          if("break".equals(kind))return "الآن: الفسحة";
          String cls="";
          for(int j=0;j<slots.length();j++){
            JSONObject slot=slots.getJSONObject(j);
            if(slot.optInt("weekday",-1)==weekday&&slot.optInt("period",-1)==number){
              String item=slot.optString("className",slot.optString("classId",""));
              if(item.isEmpty()&&!slot.optString("dutyPriority","").isEmpty())item="احتياط "+slot.optString("dutyPriority");
              if(!item.isEmpty())cls+=(cls.isEmpty()?"":"، ")+item;
            }
          }
          if(cover!=null)for(int j=0;j<cover.length();j++){
            JSONObject c=cover.getJSONObject(j);
            if(LocalDate.now().toString().equals(c.optString("date"))&&number==c.optInt("period",-1)){
              cls+=(cls.isEmpty()?"":"، ")+"احتياط مؤكد "+c.optString("classId","");
            }
          }
          return "الحصة "+number+" الآن  •  "+(cls.isEmpty()?"لا توجد حصة":cls)+"\n"+clock(t.optString("start"),t.optString("end"));
        }catch(Exception ignored){}
      }
      return "لا توجد حصة جارية الآن";
    }catch(Exception e){return "افتح الدفتر لتحديث الجدول";}
  }
  private static String clock(String start,String end){
    // Unicode isolate marks keep LTR times in their correct order inside Arabic UI.
    return "\u2066"+start+" - "+end+"\u2069";
  }
  private static CharSequence buildText(Context ctx){
    try{
      String json=ctx.getSharedPreferences("widget",Context.MODE_PRIVATE).getString("snapshot",null);
      if(json==null)return "افتح دفتر المعلم واضغط تحديث الويدجت";
      JSONObject data=new JSONObject(json);
      JSONArray slots=data.getJSONArray("slots");
      JSONArray timing=data.getJSONArray("timing");
      JSONArray cover=data.optJSONArray("cover");
      int weekday=(LocalDate.now().getDayOfWeek().getValue()%7)+1;
      String date=LocalDate.now().toString();
      SpannableStringBuilder out=new SpannableStringBuilder();
      int number=0;
      LocalTime now=LocalTime.now();
      for(int i=0;i<timing.length();i++){
        JSONObject t=timing.getJSONObject(i);
        String kind=t.optString("kind","lesson");
        String start=t.optString("start","");
        String end=t.optString("end","");
        if("assembly".equals(kind)){out.append("الطابور  ").append(clock(start,end)).append("\n");continue;}
        if("break".equals(kind)){out.append("الفسحة  ").append(clock(start,end)).append("\n");continue;}
        number++;
        String classes="";
        for(int j=0;j<slots.length();j++){
          JSONObject s=slots.getJSONObject(j);
          if(s.optInt("weekday",-1)==weekday && s.optInt("period",-1)==number){
            String cls=s.optString("className",s.optString("classId",""));
            String duty=s.optString("dutyPriority","");
            if(!cls.isEmpty())classes+= (classes.isEmpty()?"":"، ")+cls;
            else if(!duty.isEmpty())classes+=(classes.isEmpty()?"":"، ")+"احتياط "+duty;
          }
        }
        if(cover!=null)for(int j=0;j<cover.length();j++){
          JSONObject c=cover.getJSONObject(j);
          if(date.equals(c.optString("date")) && number==c.optInt("period",-1)){
            classes+=(classes.isEmpty()?"":"، ")+"احتياط مؤكد "+c.optString("classId","");
          }
        }
        String line="الحصة "+number+"  "+clock(start,end)+"  "+(classes.isEmpty()?"—":classes)+"\n";
        int offset=out.length();
        out.append(line);
        try{
          LocalTime from=LocalTime.parse(start);
          LocalTime until=LocalTime.parse(end);
          if(!now.isBefore(from) && now.isBefore(until)){
            out.setSpan(new ForegroundColorSpan(0xFF9A6913),offset,out.length(),Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            out.setSpan(new StyleSpan(Typeface.BOLD),offset,out.length(),Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
          }
        }catch(Exception ignored){} 
      }
      // Display all eight school periods even if the imported timing omits a period.
      for(int p=number+1;p<=8;p++){
        StringBuilder classes=new StringBuilder();
        for(int j=0;j<slots.length();j++){
          JSONObject slot=slots.getJSONObject(j);
          if(slot.optInt("weekday",-1)==weekday&&slot.optInt("period",-1)==p){
            String cls=slot.optString("className",slot.optString("classId",""));
            if(cls.isEmpty()&&!slot.optString("dutyPriority","").isEmpty())cls="احتياط "+slot.optString("dutyPriority");
            if(!cls.isEmpty()){if(classes.length()>0)classes.append("، ");classes.append(cls);}
          }
        }
        out.append("الحصة ").append(String.valueOf(p)).append("  ").append(classes.length()>0?classes:"—").append("\n");
      }
      return out;
    }catch(Exception e){return "تعذر قراءة الجدول. افتح الدفتر لتحديث الويدجت.";}
  }
}
