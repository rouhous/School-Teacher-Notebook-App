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
    Intent intent=new Intent(ctx,MainActivity.class);
    PendingIntent open=PendingIntent.getActivity(ctx,0,intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    view.setOnClickPendingIntent(R.id.widget_content,open);
    view.setOnClickPendingIntent(R.id.widget_title,open);
    mgr.updateAppWidget(id,view);
  }
  private static String buildText(Context ctx){
    try{
      String json=ctx.getSharedPreferences("widget",Context.MODE_PRIVATE).getString("snapshot",null);
      if(json==null)return "افتح دفتر المعلم واضغط تحديث الويدجت";
      JSONObject data=new JSONObject(json);
      JSONArray slots=data.getJSONArray("slots");
      JSONArray timing=data.getJSONArray("timing");
      JSONArray cover=data.optJSONArray("cover");
      int weekday=LocalDate.now().getDayOfWeek().getValue();
      String date=LocalDate.now().toString();
      StringBuilder out=new StringBuilder();
      int number=0;
      for(int i=0;i<timing.length();i++){
        JSONObject t=timing.getJSONObject(i);
        String kind=t.optString("kind","lesson");
        String start=t.optString("start","");
        String end=t.optString("end","");
        if("assembly".equals(kind)){out.append("الطابور  ").append(start).append("–").append(end).append("\n");continue;}
        if("break".equals(kind)){out.append("الفسحة  ").append(start).append("–").append(end).append("\n");continue;}
        number++;
        String classes="";
        for(int j=0;j<slots.length();j++){
          JSONObject s=slots.getJSONObject(j);
          if(s.optInt("weekday",-1)==weekday && s.optInt("period",-1)==number){
            String cls=s.optString("classId","");
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
        out.append("الحصة ").append(number).append("  ").append(start).append("–").append(end).append("  ").append(classes.isEmpty()?"—":classes).append("\n");
      }
      return out.toString();
    }catch(Exception e){return "تعذر قراءة الجدول. افتح الدفتر لتحديث الويدجت.";}
  }
}
