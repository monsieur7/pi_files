void setup() {
  // put your setup code here, to run once:
Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:
  //humiditeSol|temperatureAir|humiditeAir|niveauEau

Serial.println("50|20|70|30");
}
