package om.school.notebookwidget;
import android.content.Context;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;
import org.json.*;
import java.time.*;
import java.util.*;

final class WidgetUi {
 static final String URL="https://rouhous.github.io/School-Teacher-Notebook-App/school-edition/school-notebook.html";
 static int id(Context c,String name){return c.getResources().getIdentifier(name,"id",c.getPackageName());}
 static void text(Context c,RemoteViews v,String id,String txt){v.setTextViewText(id(c,id),txt);}
 static JSONObject snapshot(Context c){try{return new JSONObject(c.getSharedPreferences("widget",0).getString("snapshot","{}"));}catch(Exception e){return new JSONObject();}}
 static JSONArray array(JSONObject o,String key){JSONArray a=o.optJSONArray(key);return a==null?new JSONArray():a;}
 static int weekday(){return LocalDate.now().getDayOfWeek().getValue()%7+1;}
 static String clock(String start,String end){return "\u2066"+start+" – "+end+"\u2069";}
 static boolean active(String start,String end){try{LocalTime n=LocalTime.now();return !n.isBefore(LocalTime.parse(start))&&n.isBefore(LocalTime.parse(end));}catch(Exception e){return false;}}
 static String slot(JSONObject data,int day,int period){
  JSONArray a=array(data,"slots");StringJoiner join=new StringJoiner("، ");
  for(int i=0;i<a.length();i++){JSONObject x=a.optJSONObject(i);if(x==null||x.optInt("weekday")!=day||x.optInt("period")!=period)continue;
   String cls=x.optString("className",x.optString("classId",""));if(!cls.isEmpty())join.add(cls);
   else if(!x.optString("dutyPriority","").isEmpty())join.add("احتياط "+x.optString("dutyPriority"));
  }
  if(day==weekday())for(int i=0;i<array(data,"cover").length();i++){JSONObject x=array(data,"cover").optJSONObject(i);
   if(x!=null&&LocalDate.now().toString().equals(x.optString("date"))&&period==x.optInt("period")&&"confirmed".equals(x.optString("status","confirmed")))join.add("احتياط "+x.optString("classId",""));}
  String s=join.toString();return s.isEmpty()?"—":s;
 }
 static int[] kinds(JSONObject data){JSONArray timing=array(data,"timing");int[] a=new int[Math.min(10,timing.length())];for(int i=0;i<a.length;i++){String k=timing.optJSONObject(i)==null?"":timing.optJSONObject(i).optString("kind");a[i]="assembly".equals(k)?-1:("break".equals(k)?0:1);}return a;}
 static void shortcuts(Context ctx,RemoteViews v){String[] keys={"home","attendance","grades","now","reports"};String[] dest={"home","att","grades","live","reports"};for(int i=0;i<keys.length;i++){
  Intent in=new Intent(Intent.ACTION_VIEW,Uri.parse(URL+"#widget-"+dest[i]));in.addCategory(Intent.CATEGORY_BROWSABLE);
  PendingIntent pi=PendingIntent.getActivity(ctx,500+i,in,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);v.setOnClickPendingIntent(id(ctx,"action_"+keys[i]),pi);
 }}
 static void open(Context c,RemoteViews v,String key,int req){Intent in=new Intent(Intent.ACTION_VIEW,Uri.parse(URL+"#widget-home"));PendingIntent p=PendingIntent.getActivity(c,req,in,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);v.setOnClickPendingIntent(id(c,key),p);}
 private WidgetUi(){}
}
