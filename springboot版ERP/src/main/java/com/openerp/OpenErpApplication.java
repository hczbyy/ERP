package com.openerp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

@SpringBootApplication
@EnableCaching
public class OpenErpApplication {
   public static void main(String[] args) {
      SpringApplication.run(OpenErpApplication.class, args);
   }
}
