package stravasocial.config;

public interface AppConfig {
	public String getString(String key, String defaultValue);

	public int getInt(String key, int defaultValue);

	public long getLong(String key, int defaultValue);

	public boolean getBoolean(String key, boolean defaultValue);

	/**
	 * Sets an instance-level override. This will trump everything including
	 * dynamic properties and system properties. Useful for tests.
	 * 
	 * @param key
	 * @param value
	 */
	public void setOverrideProperty(String key, Object value);
}
