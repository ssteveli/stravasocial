package stravasocial.loader;

import org.gearman.client.GearmanJobResult;
import org.gearman.worker.AbstractGearmanFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.netflix.servo.monitor.BasicCounter;
import com.netflix.servo.monitor.BasicTimer;
import com.netflix.servo.monitor.Counter;
import com.netflix.servo.monitor.MonitorConfig;
import com.netflix.servo.monitor.Stopwatch;
import com.netflix.servo.monitor.Timer;

public class StravaActivityLoaderFunction extends AbstractGearmanFunction {
	private static Logger log = LoggerFactory.getLogger(StravaActivityLoaderFunction.class);
	private final Timer t = new BasicTimer(MonitorConfig.builder("stravaDataLoadTimer").build());
	private final Counter successCounter = new BasicCounter(MonitorConfig.builder("stravaDataLoadSuccess").build());
	private final Counter errorCounter = new BasicCounter(MonitorConfig.builder("stravaDataLoadError").build());
	
	@Override
	public GearmanJobResult executeFunction() {
		Stopwatch sw = t.start();
		try {
		
			successCounter.increment();
		} catch (Exception e) {
			log.error("error during data load", e);
			errorCounter.increment();
		} finally {
			sw.stop();
		}
		
		return null;
	}
}
