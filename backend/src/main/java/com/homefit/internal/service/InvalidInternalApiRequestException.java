package com.homefit.internal.service;

public class InvalidInternalApiRequestException extends RuntimeException {

    public InvalidInternalApiRequestException(String message) {
        super(message);
    }
}
