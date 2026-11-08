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

public class WeeklyScheduleWidget extends AppWidgetProvider {
  public static void refresh(Context ctx){
    AppWidgetManager manager=AppWidgetManager.getInstance(ctx);
    int[] ids=manager.getAppWidgetIds(new ComponentName(ctx,WeeklyScheduleWidget.class));
    for(int id:ids)render(ctx,manager,id);
  }
  @Override public void onUpdate(Context ctx,AppWidgetManager manager,int[] ids){
    for(int id:ids)render(ctx,manager,id);
  }
  private static void render(Context ctx,AppWidgetManager manager,int id){
    RemoteViews v=new RemoteViews(ctx.getPackageName(),R.layout.widget_weekly);
    v.setTextViewText(R.id.weekly_content,weeklyText(ctx));
    PendingIntent open=PendingIntent.getActivity(ctx,0,new Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://rouhous.github.io/School-Teacher-Notebook-App/")),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    v.setOnClickPendingIntent(R.id.weekly_title,open);
    v.setOnClickPendingIntent(R.id.weekly_content,open);
    manager.updateAppWidget(id,v);
  }
  private static String weeklyText(Context ctx){
    try{
      String raw=ctx.getSharedPreferences("widget",Context.MODE_PRIVATE).getString("snapshot",null);
      if(raw==null)return "افتح دفتر المعلم لعرض جدولك الأسبوعي تلقائيًا";
      JSONObject data=new JSONObject(raw);
      JSONArray slots=data.getJSONArray("slots"),timing=data.getJSONArray("timing");
      String[] days={"الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس"};
      StringBuilder out=new StringBuilder();
      for(int d=1;d<=5;d++){
        out.append("◆ ").append(days[d-1]).append("\n");
        int period=0;
        for(int t=0;t<timing.length();t++){
          JSONObject time=timing.getJSONObject(t);
          String kind=time.optString("kind","lesson");
          if("assembly".equals(kind))continue;
          if("break".equals(kind)){out.append("  الفسحة\n");continue;}
          period++;
          StringBuilder classes=new StringBuilder();
          for(int j=0;j<slots.length();j++){
            JSONObject slot=slots.getJSONObject(j);
            if(slot.optInt("weekday",-1)==d&&slot.optInt("period",-1)==period){
              String name=slot.optString("className",slot.optString("classId",""));
              if(name.isEmpty()&&!slot.optString("dutyPriority","").isEmpty())name="احتياط "+slot.optString("dutyPriority");
              if(!name.isEmpty()){if(classes.length()>0)classes.append("، ");classes.append(name);}
            }
          }
          out.append("  ").append(period).append("  ").append(classes.length()>0?classes:"—").append("\n");
        }
        if(d<5)out.append("\n");
      }
      return out.toString();
    }catch(Exception e){return "تعذر قراءة الجدول. افتح الدفتر لتحديثه.";}
  }
}