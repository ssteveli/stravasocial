package stravasocial.loader;

import org.gearman.common.GearmanNIOJobServerConnection;
import org.gearman.worker.GearmanWorker;
import org.gearman.worker.GearmanWorkerImpl;
import org.springframework.context.support.ClassPathXmlApplicationContext;

import stravasocial.config.AppConfig;

public class StravaActivityLoaderRunner {
	private GearmanNIOJobServerConnection conn;
	
	private StravaActivityLoaderRunner() {
	}
	
	private void start() {
		GearmanWorker gw = new GearmanWorkerImpl();
		gw.addServer(conn);
		gw.registerFunction(StravaActivityLoaderFunction.class);
		gw.work();
	}
	
	public static void main(String[] args) throws Exception {
		ClassPathXmlApplicationContext ctx = new ClassPathXmlApplicationContext("/strava-loader.xml");
		StravaActivityLoaderRunner instance = new StravaActivityLoaderRunner();
		instance.conn = ctx.getBean(GearmanNIOJobServerConnection.class);
		
		instance.start();
	}
}
