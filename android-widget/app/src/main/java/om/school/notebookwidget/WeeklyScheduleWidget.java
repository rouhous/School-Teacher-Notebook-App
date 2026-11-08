package om.school.notebookwidget;
import android.appwidget.*;
import android.content.*;
import android.widget.*;
import org.json.*;
import java.time.*;
public class WeeklyScheduleWidget extends AppWidgetProvider {
 public static void refresh(Context c){AppWidgetManager m=AppWidgetManager.getInstance(c);for(int i:m.getAppWidgetIds(new ComponentName(c,WeeklyScheduleWidget.class)))render(c,m,i);}
 @Override public void onUpdate(Context c,AppWidgetManager m,int[] ids){for(int i:ids)render(c,m,i);}
 private static void render(Context c,AppWidgetManager m,int id){
  RemoteViews v=new RemoteViews(c.getPackageName(),R.layout.widget_weekly);JSONObject data=WidgetUi.snapshot(c);
  JSONArray timing=WidgetUi.array(data,"timing");int period=0;
  WidgetUi.text(c,v,"weekly_subtitle",timing.length()==0?"شارك جدولك من دفتر المعلم":"الجدول المعتمد • اضغط على أحد الاختصارات لفتح الدفتر");
  for(int row=0;row<10;row++){
   JSONObject t=row<timing.length()?timing.optJSONObject(row):null;
   String kind=t==null?"":t.optString("kind","lesson");boolean isBreak="break".equals(kind);boolean assembly="assembly".equals(kind);
   String label=t==null?"":assembly?"الطابور":isBreak?"فسحة":"ح"+(++period)+"\n"+t.optString("start","");
   WidgetUi.text(c,v,"week_period_"+row,label);
   for(int day=0;day<5;day++){
    String cell="";boolean now=false;
    if(t!=null){cell=isBreak?"فسحة":assembly?"طابور":WidgetUi.slot(data,day,period);
     now=WidgetUi.weekday()==day && WidgetUi.active(t.optString("start",""),t.optString("end",""));}
    String name="week_cell_"+row+"_"+day;
    WidgetUi.text(c,v,name,cell);
    v.setInt(WidgetUi.id(c,name),"setBackgroundResource",now?R.drawable.widget_cell_active:isBreak?R.drawable.widget_cell_break:R.drawable.widget_cell);
   }
   v.setViewVisibility(WidgetUi.id(c,"week_period_"+row),t==null?android.view.View.INVISIBLE:android.view.View.VISIBLE);
  }
  WidgetUi.shortcuts(c,v);WidgetUi.open(c,v,"weekly_title",900);m.updateAppWidget(id,v);
 }
}
