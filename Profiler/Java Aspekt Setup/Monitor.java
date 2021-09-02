package de.mypackage.aspects;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;

import javax.management.Attribute;
import javax.management.AttributeList;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.io.FileWriter;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;

@Slf4j
@Aspect
public class Monitor {
    private FileWriter csvWriter = new FileWriter("./callLog.csv", true);

    long startTime;
    long startNano;

    public Monitor() throws IOException {
        this.startTime = System.currentTimeMillis() * 1000000;
        this.startNano = System.nanoTime();
    }

    @Around("execution(* *(..)) && !@annotation(de.mypackage.aspects.NoLogging)")
    public Object log(ProceedingJoinPoint pjp) throws Throwable{


        long t = this.startTime + (System.nanoTime() - this.startNano);

        csvWriter.append("start " + pjp.getSignature().toShortString().split("\\(")[0] + " " + t + "\n");
        Object result = pjp.proceed();
        t = this.startTime + (System.nanoTime() - this.startNano);
        csvWriter.append("end "  + pjp.getSignature().toShortString().split("\\(")[0] + " " + t + "\n");
        csvWriter.flush();

        return result;
    }

    public void signifyRoot(long t2, String name, String denom) throws IOException {
        t2 *= 1000000;
        csvWriter.append(denom+"Root " + name + " " + t2 + "\n");
        csvWriter.flush();
    }
}
