package stravasocial.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.InitializingBean;

import com.netflix.config.ConcurrentCompositeConfiguration;
import com.netflix.config.ConfigurationManager;
import com.netflix.config.DynamicBooleanProperty;
import com.netflix.config.DynamicIntProperty;
import com.netflix.config.DynamicLongProperty;
import com.netflix.config.DynamicPropertyFactory;
import com.netflix.config.DynamicStringProperty;

public class NetflixConfigImpl implements AppConfig, InitializingBean {
	private static Logger log = LoggerFactory.getLogger(NetflixConfigImpl.class);
	
	private String appId;
	private String env;
	
	public void afterPropertiesSet() throws Exception {
		appId = ConfigurationManager.getDeploymentContext().getApplicationId();
		env = ConfigurationManager.getDeploymentContext().getDeploymentEnvironment();
		
		log.info("config set to application [{}], environment [{}]", appId, env);
	}

	@Override
	public String getString(String key, String defaultValue) {
		final DynamicStringProperty property = DynamicPropertyFactory
				.getInstance().getStringProperty(key, defaultValue);
		return property.get();
	}

	@Override
	public int getInt(String key, int defaultValue) {
		final DynamicIntProperty property = DynamicPropertyFactory
				.getInstance().getIntProperty(key, defaultValue);
		return property.get();
	}

	@Override
	public long getLong(String key, int defaultValue) {
		final DynamicLongProperty property = DynamicPropertyFactory
				.getInstance().getLongProperty(key, defaultValue);
		return property.get();
	}

	@Override
	public boolean getBoolean(String key, boolean defaultValue) {
		final DynamicBooleanProperty property = DynamicPropertyFactory
				.getInstance().getBooleanProperty(key, defaultValue);
		return property.get();
	}

	@Override
	public void setOverrideProperty(String key, Object value) {
		((ConcurrentCompositeConfiguration) ConfigurationManager
				.getConfigInstance()).setOverrideProperty(key, value);
	}

}
