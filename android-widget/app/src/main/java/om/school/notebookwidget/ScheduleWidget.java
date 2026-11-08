package om.school.notebookwidget;
import android.appwidget.*;
import android.content.*;
import android.widget.*;
import org.json.*;
import java.time.*;
public class ScheduleWidget extends AppWidgetProvider {
 public static void refresh(Context ctx){AppWidgetManager m=AppWidgetManager.getInstance(ctx);for(int i:m.getAppWidgetIds(new ComponentName(ctx,ScheduleWidget.class)))render(ctx,m,i);}
 @Override public void onUpdate(Context c,AppWidgetManager m,int[] ids){for(int id:ids)render(c,m,id);}
 private static void render(Context c,AppWidgetManager m,int id){
  RemoteViews v=new RemoteViews(c.getPackageName(),R.layout.widget_schedule);JSONObject data=WidgetUi.snapshot(c);
  WidgetUi.text(c,v,"widget_date",LocalDate.now()+"  •  "+new String[]{"الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت"}[LocalDate.now().getDayOfWeek().getValue()%7]);
  JSONArray timing=WidgetUi.array(data,"timing");int number=0;String current="لا توجد حصة جارية الآن";boolean hasData=timing.length()>0;
  for(int i=0;i<10;i++){
   String label="",time="",subject="";boolean active=false;int bg=R.drawable.widget_cell;
   JSONObject t=i<timing.length()?timing.optJSONObject(i):null;
   if(t!=null){String kind=t.optString("kind","lesson"),start=t.optString("start",""),end=t.optString("end","");
    time=WidgetUi.clock(start,end);active=WidgetUi.active(start,end);
    if("assembly".equals(kind)){label="الطابور";subject="الطابور الصباحي";}
    else if("break".equals(kind)){label="فسحة";subject="استراحة";bg=R.drawable.widget_cell_break;}
    else{number++;label="ح"+number;subject=WidgetUi.slot(data,WidgetUi.weekday(),number);}
    if(active){bg=R.drawable.widget_cell_active;current=label+" الآن  •  "+subject+"\n"+time;}
   }else if(i<8 && !hasData){label="";subject=i==0?"شارك جدولك من دفتر المعلم":"";}
   v.setViewVisibility(WidgetUi.id(c,"daily_row_"+i),t==null?android.view.View.GONE:android.view.View.VISIBLE);
   WidgetUi.text(c,v,"day_label_"+i,label);WidgetUi.text(c,v,"day_time_"+i,time);WidgetUi.text(c,v,"day_class_"+i,subject);
   v.setInt(WidgetUi.id(c,"daily_row_"+i),"setBackgroundResource",bg);
  }
  if(!hasData)current="اربط الجدول عبر زر مشاركة في دفتر المعلم";
  WidgetUi.text(c,v,"widget_current",current);
  WidgetUi.shortcuts(c,v);WidgetUi.open(c,v,"widget_title",800);WidgetUi.open(c,v,"widget_current",801);
  m.updateAppWidget(id,v);
 }
}
